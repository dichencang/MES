// 路由：静态路由（登录/403/404）+ 动态路由（按 /permissions/my 的 tree 生成）。
// component 字符串由后端下发，相对 views 省略扩展名；未知组件渲染占位页不白屏。
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTabsStore } from '@/stores/tabs'
import { tokenStore } from '@/api/request'
import { APP_TITLE } from '@/constants'

const modules = import.meta.glob('@/views/**/*.vue')

/** 将后端 component（如 system/user/index）映射为异步组件。按后缀匹配，不依赖 glob key 前缀。 */
function resolveComponent(component: string) {
  const suffix = `/${component}.vue`
  const key = Object.keys(modules).find((k) => k.endsWith(suffix))
  const loader = key ? modules[key] : undefined
  return loader ?? (() => import('@/views/error/Placeholder.vue'))
}

const staticRoutes: RouteRecordRaw[] = [
  { path: '/login', name: 'Login', component: () => import('@/views/login/index.vue'), meta: { public: true, title: '登录' } },
  { path: '/403', name: 'Forbidden', component: () => import('@/views/error/403.vue'), meta: { public: true, title: '无权访问' } },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/error/404.vue'), meta: { title: '页面不存在' } },
]

/**
 * 前端自有路由：需要路径参数的编辑/查看页无法由权限树下发（节点 path 是固定绝对路径，没有 params 位置）。
 * 依据《契约-基础数据》v1.2 §8.1：后端只建 4 个列表 MENU，编辑/详情页由本文件注册。
 * meta.permCode 为主校验；meta.alsoPerm 为**必须同时具备**的附加校验
 * （编辑页既要 update 也要 query —— 刷新页面需调详情接口，只有 update 会打不开）。
 */
export const extraRoutes: RouteRecordRaw[] = [
  {
    path: '/basic/bom/edit/:id', name: 'basic-bom-edit',
    component: () => import('@/views/basic/bom/Edit.vue'),
    meta: { title: '编辑 BOM', permCode: 'basic:bom:update', alsoPerm: ['basic:bom:query'] },
  },
  {
    path: '/basic/bom/view/:id', name: 'basic-bom-view',
    component: () => import('@/views/basic/bom/View.vue'),
    meta: { title: '查看 BOM', permCode: 'basic:bom:query' },
  },
  {
    path: '/basic/routing/edit/:id', name: 'basic-routing-edit',
    component: () => import('@/views/basic/routing/Edit.vue'),
    meta: { title: '编辑工艺路线', permCode: 'basic:routing:update', alsoPerm: ['basic:routing:query'] },
  },
  {
    path: '/basic/routing/view/:id', name: 'basic-routing-view',
    component: () => import('@/views/basic/routing/View.vue'),
    meta: { title: '查看工艺路线', permCode: 'basic:routing:query' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
  // 切换页面回到顶部，避免长列表页残留滚动位置
  scrollBehavior: () => ({ top: 0 }),
})

const DYNAMIC_ROUTE_NAME = 'Layout'

/**
 * 依据权限树注册动态路由。**幂等**：每次先移除旧的再重建。
 * 早期用模块级 dynamicAdded 做「只注册一次」的标记，一旦标记为 true 而路由实际已被移除
 * （HMR、会话切换、异常中断），登录后会落到 catch-all 的 404——因此改为以 router.hasRoute 为准。
 * 返回首页路径供登录后跳转。
 */
export function addDynamicRoutes(): string {
  const auth = useAuthStore()
  if (router.hasRoute(DYNAMIC_ROUTE_NAME)) router.removeRoute(DYNAMIC_ROUTE_NAME)

  const children: RouteRecordRaw[] = []
  const collect = (nodes: typeof auth.navTree) => {
    for (const n of nodes) {
      // 目录(DIR)不生成路由，但必须继续递归其子级——菜单都挂在目录下
      if (n.permType === 'MENU' && n.path && n.component) {
        children.push({
          path: n.path,
          name: `perm-${n.permissionCode}`,
          component: resolveComponent(n.component),
          meta: { title: n.permName, permCode: n.permissionCode, icon: n.icon ?? undefined },
        })
      }
      if (n.children?.length) collect(n.children)
    }
  }
  collect(auth.navTree)

  if (children.length) {
    router.addRoute({
      path: '/',
      name: DYNAMIC_ROUTE_NAME,
      component: () => import('@/layout/index.vue'),
      children: [
        { path: '', name: 'LayoutHome', redirect: children[0]?.path as string },
        ...children,
        // 带 :id 的编辑/查看页：权限树下发不了，随 Layout 一起注册
        ...extraRoutes,
      ],
    })
  }
  return firstPath(auth.navTree)
}

function firstPath(nodes: ReturnType<typeof useAuthStore>['navTree']): string {
  for (const n of nodes) {
    if (n.permType === 'MENU' && n.path) return n.path
    const sub = firstPath(n.children ?? [])
    if (sub) return sub
  }
  return '/403'
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!tokenStore.access) return { path: '/login', query: { redirect: to.fullPath } }
  if (!auth.loaded) {
    try {
      await auth.loadProfile()
      addDynamicRoutes()
      // 只按路径重新解析，不能展开整个 to：首次加载时 to 匹配的是 catch-all，
      // 展开会带上 name:'NotFound'，导航时按 name 优先 → 又回到 404（刷新页面必现）。
      return { path: to.path, query: to.query, hash: to.hash, replace: true }
    } catch {
      auth.reset()
      return { path: '/login' }
    }
  }
  // 主编码 + 附加编码都要具备（编辑页需要 update 与 query 双码）
  const need = [to.meta.permCode as string, ...((to.meta.alsoPerm as string[] | undefined) ?? [])]
  if (need.some((code) => code && !auth.hasPerm(code))) return { path: '/403' }
  return true
})

router.afterEach((to) => {
  const title = (to.meta.title as string) || ''
  document.title = title ? `${title} · ${APP_TITLE}` : APP_TITLE
})

// 会话失效事件：清状态、清页签并跳登录
window.addEventListener('mes:unauthorized', () => {
  const auth = useAuthStore()
  auth.reset()
  useTabsStore().clear()
  if (router.currentRoute.value.path !== '/login') router.push('/login')
})

export default router
