<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="基础数据"
    note="物料、BOM、工序、工艺路线与检验标准，是计划与工单的公共主数据。"
    :features="['物料与物料分类、单位字典', '产品 BOM 结构维护', '工序与工艺路线编排', '检验标准与检验项配置']"
  />
</template>
