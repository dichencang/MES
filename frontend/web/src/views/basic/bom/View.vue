<script setup lang="ts">
// BOM 只读查看页：用于生效版本与历史版本核对（契约 §8.1 view 页只需 query 权限）。
// 顶部可切换同产品版本；明细显示**当前**物料名称与状态（不冻结快照）。
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBom } from '@/api'
import { formatDateTime } from '@/utils/time'
import { versionStatusText } from '../components/feedback'
import type { BomVersion } from '@/types'

const route = useRoute()
const router = useRouter()
const detail = ref<BomVersion | null>(null)
const loading = ref(true)

const id = computed(() => String(route.params.id ?? ''))
const items = computed(() => [...(detail.value?.items ?? [])].sort((a, b) => (a.sortNo ?? 0) - (b.sortNo ?? 0)))

async function load() {
  loading.value = true
  try {
    detail.value = await getBom(id.value)
  } finally {
    loading.value = false
  }
}

watch(id, load)
onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <el-card>
      <template #header>
        <div class="head">
          <div class="head-left">
            <el-button link @click="router.push('/basic/bom')">← 返回列表</el-button>
            <span class="title">{{ detail?.productCode }} {{ detail?.productName }}</span>
            <el-tag v-if="detail" size="small" :type="detail.status === '1' ? 'success' : 'info'">
              {{ detail ? versionStatusText(detail.status) : '' }} {{ detail?.versionLabel }}
            </el-tag>
          </div>
          <el-button
            v-if="detail && detail.status === '0'"
            type="primary"
            plain
            @click="router.push(`/basic/bom/edit/${detail.id}`)"
          >
            编辑草稿
          </el-button>
        </div>
      </template>

      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="基准产量">{{ detail?.baseQty ?? '—' }}</el-descriptions-item>
        <el-descriptions-item label="生效版本">
          {{ detail?.activeVersion ? `${detail.activeVersion.versionLabel}（${detail.activeVersion.publisherName}）` : '未配置' }}
        </el-descriptions-item>
        <el-descriptions-item label="最后保存人">{{ detail?.lastEditorName || '—' }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(detail?.updateTime) }}</el-descriptions-item>
      </el-descriptions>

      <el-table :data="items" border size="small" class="lines">
        <el-table-column label="#" type="index" width="56" />
        <el-table-column label="子件编码" width="150" prop="materialCode" />
        <el-table-column label="子件名称" min-width="200" prop="materialName" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.materialStatus === '1'" size="small" type="danger">已停用</el-tag>
            <span v-else>正常</span>
          </template>
        </el-table-column>
        <el-table-column label="单位" width="90" prop="unitName" />
        <el-table-column label="用量" width="120" prop="qty" />
        <template #empty>
          <el-empty description="暂无子件" :image-size="60" />
        </template>
      </el-table>

      <div class="versions">
        <span class="lines-title">同产品版本</span>
        <el-tag
          v-for="v in detail?.versions ?? []"
          :key="v.id"
          :type="v.id === detail?.id ? 'primary' : v.status === '1' ? 'success' : 'info'"
          size="small"
          class="vtag"
          @click="router.push(`/basic/bom/view/${v.id}`)"
        >
          {{ v.versionLabel }} · {{ versionStatusText(v.status) }}
          <template v-if="v.publishedAt"> · {{ formatDateTime(v.publishedAt) }}</template>
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.title {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lines {
  margin-top: 16px;
}
.lines-title {
  font-weight: 600;
}
.versions {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.vtag {
  cursor: pointer;
}
</style>
