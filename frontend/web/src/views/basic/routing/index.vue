<script setup lang="ts">
// 工艺路线列表：产品维度，与 BOM 列表同构（契约 §5.3 共用 §4.3 摘要定义）。
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageTable from '@/components/common/PageTable.vue'
import { useAuthStore } from '@/stores/auth'
import { createRouting, listRoutingProducts } from '@/api'
import { PERM } from '@/constants/perm'
import { STATUS_ENABLED } from '@/constants'
import { formatDateTime } from '@/utils/time'
import type { ConfigProductRow } from '@/types'

const auth = useAuthStore()
const router = useRouter()

const loading = ref(false)
const rows = ref<ConfigProductRow[]>([])
const total = ref(0)
const query = ref({
  keyword: '',
  configStatus: 'all' as 'all' | 'configured' | 'draft-only' | 'unconfigured',
  page: 1,
  pageSize: 10,
})

const canCreate = computed(() => auth.hasPerm(PERM.basic.routing.create))
const canQuery = computed(() => auth.hasPerm(PERM.basic.routing.query))

const CONFIG_STATUS_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '已配置生效', value: 'configured' },
  { label: '仅有草稿', value: 'draft-only' },
  { label: '未配置', value: 'unconfigured' },
] as const

async function load() {
  loading.value = true
  try {
    const res = await listRoutingProducts({ ...query.value })
    rows.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function search() {
  query.value.page = 1
  return load()
}

function resetQuery() {
  query.value = { keyword: '', configStatus: 'all', page: 1, pageSize: query.value.pageSize }
  return load()
}

const gotoEdit = (id: string) => router.push(`/basic/routing/edit/${id}`)
const gotoView = (id: string) => router.push(`/basic/routing/view/${id}`)

async function createBlank(row: ConfigProductRow) {
  const res = await createRouting({ productId: row.productId })
  ElMessage.success(`已创建草稿 ${res.versionLabel}`)
  gotoEdit(res.id)
}

async function copyVersion(row: ConfigProductRow) {
  const source = row.latestDraft?.id ?? row.activeVersion?.id
  if (!source) return
  const label = row.latestDraft?.versionLabel ?? row.activeVersion?.versionLabel
  try {
    await ElMessageBox.confirm(
      `将基于「${row.productCode} ${row.productName}」的 ${label} 复制一份新草稿，源版本不受影响。`,
      '复制为新草稿',
      { type: 'info', confirmButtonText: '复制', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const res = await createRouting({ productId: row.productId, sourceVersionId: source })
  ElMessage.success(`已复制为草稿 ${res.versionLabel}`)
  gotoEdit(res.id)
}

function canCreateFor(row: ConfigProductRow): boolean {
  return canCreate.value && row.productStatus === STATUS_ENABLED && !row.activeVersion && !row.latestDraft
}

onMounted(load)
</script>

<template>
  <PageTable
    title="工艺路线"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="产品">
          <el-input v-model="query.keyword" placeholder="编码 / 名称" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="配置状态">
          <el-select v-model="query.configStatus" @change="search">
            <el-option v-for="o in CONFIG_STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column label="产品编码" width="140">
      <template #default="{ row }">
        {{ (row as ConfigProductRow).productCode }}
        <el-tag v-if="(row as ConfigProductRow).productStatus !== STATUS_ENABLED" size="small" type="info">停用</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="productName" label="产品名称" min-width="150" show-overflow-tooltip />
    <el-table-column prop="spec" label="规格" min-width="120" show-overflow-tooltip />
    <el-table-column prop="unitName" label="单位" width="70" />
    <el-table-column label="生效版本" width="150">
      <template #default="{ row }">
        <template v-if="(row as ConfigProductRow).activeVersion">
          <el-tag size="small" type="success">{{ (row as ConfigProductRow).activeVersion?.versionLabel }}</el-tag>
          <div class="meta">
            {{ (row as ConfigProductRow).activeVersion?.publisherName }} ·
            {{ formatDateTime((row as ConfigProductRow).activeVersion?.publishedAt) }}
          </div>
        </template>
        <span v-else class="muted">未配置</span>
      </template>
    </el-table-column>
    <el-table-column label="最新草稿" width="110">
      <template #default="{ row }">
        <el-tag v-if="(row as ConfigProductRow).latestDraft" size="small" type="warning">
          {{ (row as ConfigProductRow).latestDraft?.versionLabel }}
        </el-tag>
        <span v-else class="muted">—</span>
      </template>
    </el-table-column>
    <el-table-column prop="versionCount" label="版本数" width="80" />
    <el-table-column label="最近更新" width="160">
      <template #default="{ row }">{{ formatDateTime((row as ConfigProductRow).updateTime) }}</template>
    </el-table-column>
    <el-table-column label="操作" width="220" fixed="right">
      <template #default="{ row }">
        <el-button
          v-if="(row as ConfigProductRow).latestDraft && canCreate"
          link type="primary"
          @click="gotoEdit((row as ConfigProductRow).latestDraft!.id)"
        >
          继续编辑
        </el-button>
        <el-button
          v-else-if="(row as ConfigProductRow).activeVersion && canQuery"
          link type="primary"
          @click="gotoView((row as ConfigProductRow).activeVersion!.id)"
        >
          查看
        </el-button>
        <el-button
          v-if="canCreateFor(row as ConfigProductRow)"
          link type="primary"
          @click="createBlank(row as ConfigProductRow)"
        >
          新建
        </el-button>
        <el-button
          v-if="canCreate && ((row as ConfigProductRow).latestDraft || (row as ConfigProductRow).activeVersion)"
          link
          @click="copyVersion(row as ConfigProductRow)"
        >
          复制
        </el-button>
      </template>
    </el-table-column>
  </PageTable>
</template>

<style scoped>
.search :deep(.el-input),
.search :deep(.el-select) {
  width: 180px;
}
.muted {
  color: var(--el-text-color-placeholder);
}
.meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
