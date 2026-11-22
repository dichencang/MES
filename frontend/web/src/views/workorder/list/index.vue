<script setup lang="ts">
// 生产工单列表（契约-生产工单 §二/§六）。行操作仅详情；动作都在详情页（能力由 actions 驱动）。
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageTable from '@/components/common/PageTable.vue'
import { useCrud } from '@/composables/useCrud'
import { listWorkOrders, materialOptions } from '@/api'
import { PERM } from '@/constants/perm'
import { useAuthStore } from '@/stores/auth'
import { WO_STATUS_LABEL, type MaterialOption, type WorkOrderRow, type WorkOrderStatus } from '@/types'
import { formatUtcShanghai } from '@/utils/time'

const router = useRouter()
const auth = useAuthStore()

const { loading, rows, total, query, load, search, resetQuery } = useCrud<WorkOrderRow>({
  fetch: listWorkOrders,
  defaultQuery: () => ({
    workOrderNo: '', planNo: '', productId: '', status: '', dateStart: '', dateEnd: '',
  }),
})

const statusOptions = Object.entries(WO_STATUS_LABEL).map(([value, label]) => ({ value, label }))

function statusType(s: WorkOrderStatus): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  if (s === 'IN_PRODUCTION') return 'primary'
  if (s === 'COMPLETED') return 'success'
  if (s === 'CANCELLED' || s === 'CLOSED') return 'info'
  if (s === 'RELEASED') return 'warning'
  return 'danger'
}

/** 进度：finishedStepCount 首期为 null，显示"待接入"而不是 0 进度（契约 §3.1） */
function progressText(row: WorkOrderRow): string {
  if (row.finishedStepCount === null || row.finishedStepCount === undefined) return '待接入'
  return `${row.finishedStepCount}/${row.stepCount}`
}

// 产品下拉：复用会话级产品选项，不需要基础数据管理权限
const productOptions = ref<MaterialOption[]>([])
async function loadProducts(kw: string) {
  const res = await materialOptions({ keyword: kw || undefined, isProduct: true, pageSize: 20 })
  productOptions.value = res.list
}

onMounted(() => { load(); loadProducts('') })
</script>

<template>
  <PageTable
    title="生产工单"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #toolbar>
      <el-button
        v-if="auth.hasPerm(PERM.workorder.create)"
        type="primary" @click="router.push('/workorder/create')"
      >手工新建</el-button>
    </template>

    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="工单号">
          <el-input v-model="query.workOrderNo" placeholder="模糊" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="计划号">
          <el-input v-model="query.planNo" placeholder="模糊" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="产品">
          <el-select
            v-model="query.productId" filterable remote clearable
            :remote-method="loadProducts" placeholder="全部产品"
          >
            <el-option v-for="p in productOptions" :key="p.id" :value="p.id" :label="`${p.code} ${p.name}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable>
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="排期">
          <!-- 契约 §二：排期重叠查询，起止可分别省略任一端 -->
          <el-date-picker v-model="query.dateStart" type="date" value-format="YYYY-MM-DD" placeholder="开始（可空）" />
          <span class="range-sep">~</span>
          <el-date-picker v-model="query.dateEnd" type="date" value-format="YYYY-MM-DD" placeholder="结束（可空）" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column prop="workOrderNo" label="工单号" width="150" />
    <el-table-column label="产品" min-width="150" show-overflow-tooltip>
      <template #default="{ row }">
        {{ (row as WorkOrderRow).productCode }} {{ (row as WorkOrderRow).productName }}
        <span class="unit-hint">{{ (row as WorkOrderRow).unitName }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="plannedQty" label="计划数量" width="105" align="right" />
    <el-table-column label="计划开始" width="150">
      <template #default="{ row }">{{ formatUtcShanghai((row as WorkOrderRow).plannedStartAt) }}</template>
    </el-table-column>
    <el-table-column label="计划结束" width="150">
      <template #default="{ row }">{{ formatUtcShanghai((row as WorkOrderRow).plannedEndAt) }}</template>
    </el-table-column>
    <el-table-column label="状态" width="95">
      <template #default="{ row }">
        <el-tag size="small" :type="statusType((row as WorkOrderRow).status)">
          {{ WO_STATUS_LABEL[(row as WorkOrderRow).status] }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="工序进度" width="95" align="center">
      <template #default="{ row }">
        <span :class="{ muted: progressText(row as WorkOrderRow) === '待接入' }">{{ progressText(row as WorkOrderRow) }}</span>
      </template>
    </el-table-column>
    <el-table-column label="来源计划" width="140">
      <template #default="{ row }">{{ (row as WorkOrderRow).planNo || '—' }}</template>
    </el-table-column>
    <el-table-column label="操作" width="80" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" @click="router.push(`/workorder/detail/${(row as WorkOrderRow).id}`)">详情</el-button>
      </template>
    </el-table-column>
  </PageTable>
</template>

<style scoped>
.search :deep(.el-input),
.search :deep(.el-select),
.search :deep(.el-date-editor) { width: 160px; }
.range-sep { margin: 0 6px; color: var(--el-text-color-secondary); }
.unit-hint { margin-left: 4px; font-size: 12px; color: var(--el-text-color-secondary); }
.muted { color: var(--el-text-color-placeholder); }
</style>
