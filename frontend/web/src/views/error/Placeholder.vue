<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <div class="placeholder">
    <el-empty :description="`页面开发中：${route.path}`" />
  </div>
</template>

<style scoped>
.placeholder { display: flex; align-items: center; justify-content: center; min-height: 60vh; }
</style>
