<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="库存管理"
    note="入库、领料、出库、退料与流水，配合齐套分析支撑生产齐套性。"
    :features="['采购入库与成品入库', '生产领料与产品出库', '生产退料与库存流水', '实时库存与齐套分析']"
  />
</template>
