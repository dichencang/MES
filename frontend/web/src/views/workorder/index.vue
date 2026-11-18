<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="生产工单"
    note="计划的执行载体，下辖派工、报工进度与工单甘特图。"
    :features="['工单创建、下发、派工、撤销与关闭', '工单详情：BOM 子件、工艺路线、报工进度', '工单甘特图与操作日志']"
  />
</template>
