<script setup lang="ts">
// 销售订单列表（契约-计划管理 §2.6）。列表返回摘要；详情/录单/编辑为前端静态路由。
// 按钮显隐：权限（hasPerm）→ 不渲染；业务能力（详情 actions）在详情页判定。列表行只做跳转。
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageTable from '@/components/common/PageTable.vue'
import { useCrud } from '@/composables/useCrud'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/request'
import { cancelSalesOrder, listSalesOrders } from '@/api'
import { PERM } from '@/constants/perm'
import {
  SALES_ORDER_STATUS_LABEL, type SalesOrderRow, type SalesOrderStatus,
} from '@/types'

const router = useRouter()
const auth = useAuthStore()
const canceling = ref(false)

const { loading, rows, total, query, load, search, resetQuery } = useCrud<SalesOrderRow>({
  fetch: listSalesOrders,
  defaultQuery: () => ({ orderNo: '', customerName: '', status: '', dateStart: '', dateEnd: '' }),
  // 列表无新建弹窗：新建走静态路由；取消也走详情，故不配置 create/update/remove
})

const statusOptions = Object.entries(SALES_ORDER_STATUS_LABEL).map(([value, label]) => ({ value, label }))

function statusType(s: SalesOrderStatus): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  switch (s) {
    case 'COMPLETED': return 'success'
    case 'SCHEDULED': return 'primary'
    case 'IN_PRODUCTION': return 'warning'
    case 'CANCELLED': return 'danger'
    default: return 'info'
  }
}

function openView(id: string) { router.push(`/plan/sales-order/view/${id}`) }
function openEdit(id: string) { router.push(`/plan/sales-order/edit/${id}`) }

async function doCancel(row: SalesOrderRow) {
  try {
    const { value } = await ElMessageBox.prompt(
      `确认取消订单「${row.orderNo}」？请填写取消说明。`,
      '取消订单',
      {
        inputType: 'textarea', inputPlaceholder: '请输入取消原因（必填）',
        confirmButtonText: '确认取消', cancelButtonText: '返回',
        inputValidator: (v: string) => (v?.trim() ? true : '取消说明不能为空'),
      },
    )
    canceling.value = true
    await cancelSalesOrder(row.id, { cancelReason: value.trim() })
    ElMessage.success('订单已取消')
    await load()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    const err = e as ApiError
    if (err instanceof ApiError && err.code === 4100) {
      // 其余状态冲突：后端 message 已弹，这里不重复
      return
    }
  } finally {
    canceling.value = false
  }
}

onMounted(load)
</script>

<template>
  <PageTable
    title="销售订单"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #toolbar>
      <el-button v-if="auth.hasPerm(PERM.plan.salesOrder.create)" type="primary" @click="router.push('/plan/sales-order/new')">
        手工录单
      </el-button>
    </template>

    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="订单号">
          <el-input v-model="query.orderNo" placeholder="模糊" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="客户">
          <el-input v-model="query.customerName" placeholder="模糊" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable>
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="订单日期">
          <el-date-picker
            :model-value="[query.dateStart, query.dateEnd]" type="daterange" value-format="YYYY-MM-DD"
            start-placeholder="开始" end-placeholder="结束" :clearable="true"
            @change="(v: string[] | null) => { query.dateStart = v?.[0] ?? ''; query.dateEnd = v?.[1] ?? '' }"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column prop="orderNo" label="订单号" width="150" />
    <el-table-column prop="customerName" label="客户" min-width="140" show-overflow-tooltip />
    <el-table-column prop="orderDate" label="订单日期" width="120" />
    <el-table-column label="状态" width="100">
      <template #default="{ row }">
        <el-tag size="small" :type="statusType((row as SalesOrderRow).status)">
          {{ SALES_ORDER_STATUS_LABEL[(row as SalesOrderRow).status] }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="itemCount" label="明细数" width="90" align="right" />
    <el-table-column prop="scheduledItemCount" label="已排足行" width="100" align="right" />
    <el-table-column prop="createdAt" label="创建时间" width="160" />
    <el-table-column label="操作" width="200" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" @click="openView((row as SalesOrderRow).id)">详情</el-button>
        <el-button
          v-if="auth.hasPerm(PERM.plan.salesOrder.update)"
          link type="primary" @click="openEdit((row as SalesOrderRow).id)"
        >编辑</el-button>
        <el-button
          v-if="auth.hasPerm(PERM.plan.salesOrder.cancel)"
          link type="danger" :loading="canceling" @click="doCancel(row as SalesOrderRow)"
        >取消</el-button>
      </template>
    </el-table-column>
  </PageTable>
</template>

<style scoped>
.search :deep(.el-input),
.search :deep(.el-select),
.search :deep(.el-date-editor) { width: 180px; }
</style>
