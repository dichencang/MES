<script setup lang="ts">
// 工作台：按需求真源的移动端信息架构列出功能入口（骨架，点击暂未接入路由）
const groups = [
  {
    title: "计划管理",
    items: ["销售订单", "生产计划"],
  },
  {
    title: "生产管理",
    items: ["生产工单", "生产报工", "报工记录"],
  },
  {
    title: "质量管理",
    items: ["来料检验", "过程检验", "最终检验"],
  },
  {
    title: "仓库管理",
    items: ["采购入库", "生产领料", "生产退料", "产品出库", "库存查询"],
  },
];
</script>

<template>
  <view class="workbench">
    <view v-for="group in groups" :key="group.title" class="group">
      <view class="group-title">{{ group.title }}</view>
      <view class="grid">
        <view v-for="item in group.items" :key="item" class="cell">
          <view class="cell-icon">▦</view>
          <view class="cell-text">{{ item }}</view>
        </view>
      </view>
    </view>
    <view class="note">入口为骨架展示，业务页面待后端契约确认后实现</view>
  </view>
</template>

<style scoped>
.workbench {
  padding: 24rpx;
}
.group {
  background: #fff;
  border-radius: 12rpx;
  margin-bottom: 24rpx;
  padding: 24rpx;
}
.group-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #303133;
  margin-bottom: 20rpx;
  padding-left: 12rpx;
  border-left: 6rpx solid #409eff;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20rpx;
}
.cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20rpx 0;
}
.cell-icon {
  width: 88rpx;
  height: 88rpx;
  line-height: 88rpx;
  text-align: center;
  border-radius: 20rpx;
  background: #ecf5ff;
  color: #409eff;
  font-size: 40rpx;
  margin-bottom: 12rpx;
}
.cell-text {
  font-size: 24rpx;
  color: #606266;
}
.note {
  font-size: 22rpx;
  color: #c0c4cc;
  text-align: center;
  padding: 20rpx 0 40rpx;
}
</style>
