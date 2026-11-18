<script setup lang="ts">
// 业务模块占位页：菜单节点与路由已通，页面待开发。统一用它，避免每个模块各写一套空壳。
defineProps<{
  title: string
  /** 一句话说明模块定位 */
  note?: string
  /** 规划中的功能点 */
  features?: string[]
}>()
</script>

<template>
  <div class="page">
    <el-card class="placeholder">
      <div class="inner">
        <el-icon class="icon"><Grid /></el-icon>
        <h3>{{ title }}</h3>
        <p v-if="note" class="note">{{ note }}</p>

        <ul v-if="features && features.length" class="features">
          <li v-for="f in features" :key="f">{{ f }}</li>
        </ul>

        <el-tag type="info" effect="plain">待接口契约确定后开发</el-tag>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}
.placeholder :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
}
.inner {
  max-width: 520px;
  text-align: center;
}
.icon {
  font-size: 40px;
  color: #c0c4cc;
}
h3 {
  margin: 12px 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.note {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.8;
  color: #909399;
}
.features {
  display: inline-block;
  margin: 0 0 18px;
  padding: 0;
  text-align: left;
  list-style: none;
}
.features li {
  position: relative;
  padding-left: 16px;
  font-size: 13px;
  line-height: 2;
  color: #606266;
}
.features li::before {
  content: '';
  position: absolute;
  top: 12px;
  left: 2px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #c0c4cc;
}
</style>
