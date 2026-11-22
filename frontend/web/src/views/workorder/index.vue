<script setup lang="ts">
// 兼容后端 MENU 的 component 可能下发 workorder/index 或 workorder/list/index：两种都能渲染列表。
import WorkOrderList from './list/index.vue'
</script>

<template>
  <WorkOrderList />
</template>
