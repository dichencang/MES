<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="报工管理"
    note="现场扫码报工，记录合格数、不良数与工时，是产量与进度的数据来源。"
    :features="['PC 端报工录入与批量汇总', '移动端扫码报工（配合工单二维码）', 'AI 预填报工表单']"
  />
</template>
