<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { PermNode } from '@/types'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const activePath = computed(() => route.path)

// el-menu 只接受目录/菜单节点：有 children 的用 el-sub-menu，叶子用 el-menu-item
const menus = computed(() => auth.navTree)

async function handleCommand(command: string) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' })
    await auth.logout()
    router.push('/login')
  } else if (command === 'password') {
    router.push('/profile/password')
  }
}

function iconOf(node: PermNode): string {
  return node.icon || 'Document'
}
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
        <template v-for="node in menus" :key="node.id">
          <el-sub-menu v-if="node.children && node.children.length" :index="node.path || node.id">
            <template #title>
              <el-icon><component :is="iconOf(node)" /></el-icon>
              <span>{{ node.permName }}</span>
            </template>
            <el-menu-item v-for="child in node.children" :key="child.id" :index="child.path || ''">
              <el-icon><component :is="iconOf(child)" /></el-icon>
              <span>{{ child.permName }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="node.path || ''">
            <el-icon><component :is="iconOf(node)" /></el-icon>
            <span>{{ node.permName }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="crumb">{{ (route.meta.title as string) || '首页' }}</div>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><UserFilled /></el-icon>
            {{ auth.user?.realName || '未登录' }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
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
.header { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid #e8e8e8; }
.crumb { font-size: 15px; color: #303133; }
.user-info { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.main { background: #f0f2f5; padding: 16px; overflow: auto; }
</style>
