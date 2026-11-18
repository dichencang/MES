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

export const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
  // 切换页面回到顶部，避免长列表页残留滚动位置
  scrollBehavior: () => ({ top: 0 }),
})

const DYNAMIC_ROUTE_NAME = 'Layout'
let dynamicAdded = false

/** 依据权限树注册动态路由。返回首页路径供登录后跳转 */
export function addDynamicRoutes(): string {
  const auth = useAuthStore()
  if (dynamicAdded) return firstPath(auth.navTree)
  // 重新登录时先移除旧的动态路由，避免同名冲突
  if (router.hasRoute(DYNAMIC_ROUTE_NAME)) router.removeRoute(DYNAMIC_ROUTE_NAME)
  dynamicAdded = true

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
      return { ...to, replace: true }
    } catch {
      auth.reset()
      return { path: '/login' }
    }
  }
  if (!auth.hasPerm((to.meta.permCode as string) ?? '')) return { path: '/403' }
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
  dynamicAdded = false
  if (router.currentRoute.value.path !== '/login') router.push('/login')
})

export default router
