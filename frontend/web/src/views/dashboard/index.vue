<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="生产看板"
    note="面向车间的可视化大屏，展示进度、产量、合格率、产线状态与报警。"
    :features="['生产进度与工单状态', '产量与合格率趋势', '产线状态与异常报警']"
  />
</template>
