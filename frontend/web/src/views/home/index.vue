<script setup lang="ts">
// 工作台首页：登录后的落地页。当前只有欢迎区与快捷入口可用，
// 统计卡片等业务接口（工单/报工/质检/库存）就绪后接入，先显示 "—" 不造假数据。
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { APP_TITLE } from '@/constants'
import type { PermNode } from '@/types'

const auth = useAuthStore()
const router = useRouter()

const welcomeName = computed(() => auth.user?.realName || auth.user?.username || '')
const deptName = computed(() => auth.user?.deptName || '未分配部门')
const roleNames = computed(() => auth.user?.roles?.map((r) => r.roleName).join('、') || '—')
const today = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
})

/** 权限树里所有可跳转菜单，作为快捷入口 */
function collectMenus(nodes: PermNode[], acc: PermNode[] = []): PermNode[] {
  for (const n of nodes) {
    if (n.permType === 'MENU' && n.path) acc.push(n)
    if (n.children?.length) collectMenus(n.children, acc)
  }
  return acc
}
const shortcuts = computed(() => collectMenus(auth.navTree).slice(0, 8))

const stats = [
  { key: 'workorder', label: '待处理工单', hint: '工单模块接口就绪后接入' },
  { key: 'report', label: '今日报工', hint: '报工模块接口就绪后接入' },
  { key: 'quality', label: '待检任务', hint: '质检模块接口就绪后接入' },
  { key: 'stock', label: '库存预警', hint: '库存模块接口就绪后接入' },
]
</script>

<template>
  <div class="page home">
    <el-card class="hero">
      <div class="hero-main">
        <h2>你好，{{ welcomeName }}</h2>
        <p class="meta">
          <span>{{ deptName }}</span>
          <span class="dot">·</span>
          <span>{{ roleNames }}</span>
          <span class="dot">·</span>
          <span>{{ today }}</span>
        </p>
      </div>
      <div class="hero-brand">
        <span class="brand-mark">MES</span>
        <span class="brand-text">{{ APP_TITLE }}</span>
      </div>
    </el-card>

    <div class="stats">
      <el-card v-for="s in stats" :key="s.key" class="stat" shadow="never">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">—</div>
        <el-tooltip :content="s.hint" placement="top">
          <el-tag size="small" type="info" effect="plain">待接入</el-tag>
        </el-tooltip>
      </el-card>
    </div>

    <el-card class="section">
      <template #header><span class="title">快捷入口</span></template>
      <div v-if="shortcuts.length" class="shortcuts">
        <button v-for="m in shortcuts" :key="m.id" class="shortcut" @click="router.push(m.path as string)">
          <el-icon><component :is="m.icon || 'Document'" /></el-icon>
          <span>{{ m.permName }}</span>
        </button>
      </div>
      <el-empty v-else description="当前账号还没有可访问的菜单" :image-size="64" />
    </el-card>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hero {
  flex: none;
}
.hero :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.hero-main h2 {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #1f2d3d;
}
.meta {
  margin: 0;
  font-size: 13px;
  color: #909399;
}
.dot {
  margin: 0 8px;
  color: #dcdfe6;
}
.hero-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-right: 8px;
  color: #606266;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 700;
  color: #0a1a2c;
  background: linear-gradient(140deg, #8ec5ff, #4f9bf5);
}
.brand-text {
  font-size: 13px;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.stat :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}
.stat-label {
  font-size: 13px;
  color: #909399;
}
.stat-value {
  font-size: 26px;
  font-weight: 600;
  line-height: 1.1;
  color: #303133;
}
.section {
  flex: 1;
}
.shortcuts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.shortcut {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  font-size: 13px;
  color: #303133;
  background: #fafcff;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.shortcut:hover {
  border-color: #a3c8f5;
  background: #f0f7ff;
}
.shortcut .el-icon {
  font-size: 16px;
  color: #409eff;
}
</style>
