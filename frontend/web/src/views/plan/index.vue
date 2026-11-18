<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="计划管理"
    note="销售订单 → 生产计划 → 计划甘特图，是工单的上游来源。"
    :features="['销售订单录入、审核与交期管理', '生产计划编制、审核与下达', '计划甘特图（按产线与时间轴）']"
  />
</template>
