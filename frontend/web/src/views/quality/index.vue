<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="质检管理"
    note="来料、过程、最终三级检验，不合格品走返工、报废或让步处理。"
    :features="['来料检验（IQC）', '过程检验（IPQC）', '最终检验（FQC）', '不合格品处理与追溯']"
  />
</template>
