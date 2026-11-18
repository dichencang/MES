<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string;
    desc?: string;
  }>(),
  { desc: "功能开发中，敬请期待" },
);
</script>

<template>
  <view class="placeholder">
    <view class="icon">📦</view>
    <view class="title">{{ title }}</view>
    <view class="desc">{{ desc }}</view>
  </view>
</template>

<style scoped>
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 40rpx;
}
.icon {
  font-size: 96rpx;
  margin-bottom: 24rpx;
}
.title {
  font-size: 36rpx;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16rpx;
}
.desc {
  font-size: 26rpx;
  color: #909399;
}
</style>
