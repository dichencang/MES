<script setup lang="ts">
// 布局壳：可折叠侧栏（递归菜单）+ 面包屑 + 多页签 + 用户下拉。
// 侧栏与路由都由 /permissions/my 的 tree 驱动，这里不做任何权限判断（路由守卫已拦）。
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useTabsStore } from '@/stores/tabs'
import { useDictStore } from '@/stores/dict'
import { APP_TITLE } from '@/constants'
import type { PermNode } from '@/types'
import MenuNode from './components/MenuNode.vue'

const auth = useAuthStore()
const tabs = useTabsStore()
const dict = useDictStore()
const route = useRoute()
const router = useRouter()

const collapsed = ref(false)
const activePath = computed(() => route.path)
const menus = computed(() => auth.navTree)

/** 当前路径在权限树里的链路，用于面包屑 */
function findTrail(nodes: PermNode[], path: string): PermNode[] {
  for (const node of nodes) {
    if (node.path === path) return [node]
    const sub = findTrail(node.children ?? [], path)
    if (sub.length) return [node, ...sub]
  }
  return []
}

const trail = computed(() => findTrail(menus.value, route.path))

// 打开页面即记入页签
watch(
  () => route.path,
  () => {
    const title = (route.meta.title as string) || trail.value.at(-1)?.permName || '未命名页面'
    tabs.add({ path: route.path, title })
    document.title = `${title} · ${APP_TITLE}`
  },
  { immediate: true },
)

function closeTab(path: string) {
  const index = tabs.tabs.findIndex((t) => t.path === path)
  tabs.remove(path)
  if (route.path !== path) return
  const next = tabs.tabs[index - 1] ?? tabs.tabs[tabs.tabs.length - 1]
  router.push(next ? next.path : '/')
}

async function handleCommand(command: string) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
    await auth.logout()
    tabs.clear()
    dict.clear()
    router.push('/login')
  } else if (command === 'password') {
    router.push('/profile/password')
  }
}

onMounted(() => {
  if (window.innerWidth < 1280) collapsed.value = true
})
</script>

<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="logo" @click="collapsed = !collapsed">
        <span v-if="!collapsed">MES 生产执行系统</span>
        <span v-else>MES</span>
      </div>
      <el-menu
        :default-active="activePath"
        :collapse="collapsed"
        :collapse-transition="false"
        background-color="#001529"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
        unique-opened
      >
        <MenuNode v-for="node in menus" :key="node.id" :node="node" />
      </el-menu>
    </el-aside>

    <el-container class="body">
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Expand v-if="collapsed" />
            <Fold v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="node in trail" :key="node.id">{{ node.permName }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="!trail.length">{{ (route.meta.title as string) || '首页' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><UserFilled /></el-icon>
            <span class="user-name">{{ auth.user?.realName || '未登录' }}</span>
            <span v-if="auth.user?.deptName" class="user-dept">{{ auth.user.deptName }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                {{ auth.user?.roles?.map((r) => r.roleName).join('、') || '无角色' }}
              </el-dropdown-item>
              <el-dropdown-item command="password" divided>修改密码</el-dropdown-item>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <div class="tabs-bar">
        <el-tag
          v-for="tab in tabs.tabs"
          :key="tab.path"
          :type="tab.path === route.path ? 'primary' : 'info'"
          :effect="tab.path === route.path ? 'dark' : 'plain'"
          :closable="!tab.affix"
          class="tab-item"
          @click="router.push(tab.path)"
          @close="closeTab(tab.path)"
        >
          {{ tab.title }}
        </el-tag>
      </div>

      <el-main class="main">
        <RouterView v-slot="{ Component }">
          <component :is="Component" />
        </RouterView>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout { height: 100vh; }
.aside { background: #001529; transition: width 0.2s; overflow: hidden; }
.logo { height: 56px; line-height: 56px; text-align: center; color: #fff; font-weight: 600; font-size: 15px; cursor: pointer; white-space: nowrap; }
.aside .el-menu { border-right: none; }
.body { min-width: 0; }
.header { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid #e8e8e8; height: 52px; }
.header-left { display: flex; align-items: center; gap: 14px; min-width: 0; }
.collapse-btn { font-size: 18px; cursor: pointer; color: #606266; }
.collapse-btn:hover { color: #409eff; }
.user-info { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.user-name { font-size: 14px; color: #303133; }
.user-dept { font-size: 12px; color: #909399; }
.tabs-bar { display: flex; align-items: center; gap: 6px; padding: 6px 16px; background: #fff; border-bottom: 1px solid #e8e8e8; overflow-x: auto; }
.tab-item { cursor: pointer; user-select: none; }
.main { background: #f0f2f5; padding: 16px; overflow: auto; }
</style>
