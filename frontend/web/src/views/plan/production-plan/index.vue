<script setup lang="ts">
// 生产计划列表（契约-计划管理 §3.6）。列表返回摘要；详情/编辑为前端静态路由。
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageTable from '@/components/common/PageTable.vue'
import { useCrud } from '@/composables/useCrud'
import { listProductionPlans } from '@/api'
import { PLAN_STATUS_LABEL, type ProductionPlanRow, type ProductionPlanStatus } from '@/types'
import { formatUtcShanghai } from '@/utils/time'

const router = useRouter()
const { loading, rows, total, query, load, search, resetQuery } = useCrud<ProductionPlanRow>({
  fetch: listProductionPlans,
  defaultQuery: () => ({ planNo: '', orderNo: '', productId: '', status: '', dateStart: '', dateEnd: '' }),
})

const statusOptions = Object.entries(PLAN_STATUS_LABEL).map(([value, label]) => ({ value, label }))

function statusType(s: ProductionPlanStatus): 'success' | 'info' | 'warning' {
  if (s === 'TRANSFERRED') return 'success'
  if (s === 'CANCELLED') return 'info'
  return 'warning'
}

onMounted(load)
</script>

<template>
  <PageTable
    title="生产计划"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="计划号">
          <el-input v-model="query.planNo" placeholder="模糊" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="query.orderNo" placeholder="模糊" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="产品">
          <el-input v-model="query.productId" placeholder="产品 ID" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable>
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划时间">
          <el-date-picker
            :model-value="[query.dateStart, query.dateEnd]" type="daterange" value-format="YYYY-MM-DD"
            start-placeholder="开始" end-placeholder="结束"
            @change="(v: string[] | null) => { query.dateStart = v?.[0] ?? ''; query.dateEnd = v?.[1] ?? '' }"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column prop="planNo" label="计划号" width="150" />
    <el-table-column prop="orderNo" label="订单号" width="140" />
    <el-table-column prop="productName" label="产品" min-width="140" show-overflow-tooltip />
    <el-table-column prop="plannedQty" label="计划数量" width="110" align="right" />
    <el-table-column label="计划开始" width="170">
      <template #default="{ row }">{{ formatUtcShanghai((row as ProductionPlanRow).plannedStartAt) }}</template>
    </el-table-column>
    <el-table-column label="计划结束" width="170">
      <template #default="{ row }">{{ formatUtcShanghai((row as ProductionPlanRow).plannedEndAt) }}</template>
    </el-table-column>
    <el-table-column label="状态" width="100">
      <template #default="{ row }">
        <el-tag size="small" :type="statusType((row as ProductionPlanRow).status)">
          {{ PLAN_STATUS_LABEL[(row as ProductionPlanRow).status] }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="关联工单" width="130">
      <template #default="{ row }">{{ (row as ProductionPlanRow).workOrderNo || '—' }}</template>
    </el-table-column>
    <el-table-column label="操作" width="100" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" @click="router.push(`/plan/production-plan/view/${(row as ProductionPlanRow).id}`)">详情</el-button>
      </template>
    </el-table-column>
  </PageTable>
</template>

<style scoped>
.search :deep(.el-input),
.search :deep(.el-select),
.search :deep(.el-date-editor) { width: 170px; }
</style>
