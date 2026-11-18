<script setup lang="ts">
// 侧栏菜单递归节点：支持任意层级目录（DIR）→ 菜单（MENU）。
// 目录没有 path，用 id 作为 el-sub-menu 的 index，避免多个空 index 冲突。
import type { PermNode } from '@/types'

const props = defineProps<{ node: PermNode }>()

const hasChildren = (n: PermNode) => (n.children?.length ?? 0) > 0
const iconOf = (n: PermNode) => n.icon || 'Document'
</script>

<template>
  <el-sub-menu v-if="hasChildren(props.node)" :index="props.node.path || props.node.id">
    <template #title>
      <el-icon><component :is="iconOf(props.node)" /></el-icon>
      <span>{{ props.node.permName }}</span>
    </template>
    <MenuNode v-for="child in props.node.children" :key="child.id" :node="child" />
  </el-sub-menu>

  <el-menu-item v-else :index="props.node.path || props.node.id">
    <el-icon><component :is="iconOf(props.node)" /></el-icon>
    <template #title>
      <span>{{ props.node.permName }}</span>
    </template>
  </el-menu-item>
</template>
