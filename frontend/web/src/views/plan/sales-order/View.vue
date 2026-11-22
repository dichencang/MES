<script setup lang="ts">
// 销售订单详情（契约-计划管理 §2.2）。展示逐行数量与能力；从行创建计划（拆分入口一）。
//  · 权限控制显隐；actions.canCreatePlan 控制置灰 + disableReason 原因
//  · 创建计划弹窗展示订单数量/已排/可排，提交由后端校验最新余额（超额 409 时刷新该行）
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getSalesOrder, listOrderItems, createProductionPlan } from '@/api'
import { ApiError } from '@/api/request'
import { PLAN_BIZ_CODE } from '@/constants/biz'
import { PERM } from '@/constants/perm'
import { useAuthStore } from '@/stores/auth'
import {
  SALES_ORDER_STATUS_LABEL, type SalesOrderDetail, type SalesOrderItem,
  type OrderItemCandidate, type PlanCreatePayload,
} from '@/types'
import { asQuantityConflict, reasonText } from '../components/feedback'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const detail = ref<SalesOrderDetail | null>(null)

const id = computed(() => String(route.params.id))

async function load() {
  loading.value = true
  try {
    detail.value = await getSalesOrder(id.value)
  } finally {
    loading.value = false
  }
}

// ── 创建计划弹窗 ──────────────────────────────────────
const planDialog = ref(false)
const candidates = ref<OrderItemCandidate[]>([])
const planForm = reactive({
  orderItemId: '', orderNo: '', productName: '', unitName: '',
  orderQty: '', scheduledQty: '', availableQty: '',
  plannedQty: '', plannedStartAt: '', plannedEndAt: '', remark: null as string | null,
})
const planSubmitting = ref(false)

async function openCreatePlan(item?: SalesOrderItem) {
  const res = await listOrderItems({ orderNo: detail.value?.orderNo, onlyAvailable: false, pageSize: 100 })
  candidates.value = res.list
  if (item) fillPlanForm(candidates.value.find((c) => c.orderItemId === item.id) ?? null, item)
  else resetPlanForm()
  planDialog.value = true
}

function fillPlanForm(c: OrderItemCandidate | null, item?: SalesOrderItem) {
  planForm.orderItemId = c?.orderItemId ?? item?.id ?? ''
  planForm.orderNo = c?.orderNo ?? detail.value?.orderNo ?? ''
  planForm.productName = c?.productName ?? item?.productName ?? ''
  planForm.unitName = c?.unitName ?? item?.unitName ?? ''
  planForm.orderQty = c?.orderQty ?? item?.orderQty ?? ''
  planForm.scheduledQty = c?.scheduledQty ?? item?.scheduledQty ?? ''
  planForm.availableQty = c?.availableQty ?? item?.availableQty ?? ''
  planForm.plannedQty = ''
  planForm.plannedStartAt = ''
  planForm.plannedEndAt = ''
  planForm.remark = null
}

function resetPlanForm() {
  fillPlanForm(null)
}

async function onCandidateChange(oid: string) {
  const c = candidates.value.find((x) => x.orderItemId === oid)
  if (c) fillPlanForm(c)
}

async function submitPlan() {
  if (!planForm.orderItemId) { ElMessage.warning('请选择订单行'); return }
  if (!planForm.plannedQty || Number(planForm.plannedQty) <= 0) { ElMessage.warning('计划数量须大于 0'); return }
  if (!planForm.plannedStartAt || !planForm.plannedEndAt) { ElMessage.warning('请选择起止时间'); return }
  const payload: PlanCreatePayload = {
    orderItemId: planForm.orderItemId,
    plannedQty: planForm.plannedQty,
    plannedStartAt: planForm.plannedStartAt,
    plannedEndAt: planForm.plannedEndAt,
    remark: planForm.remark,
  }
  planSubmitting.value = true
  try {
    await createProductionPlan(payload)
    ElMessage.success('计划已创建')
    planDialog.value = false
    await load() // 刷新已排/可排
  } catch (e) {
    if (e instanceof ApiError && e.code === PLAN_BIZ_CODE.PLAN_QUANTITY_EXCEEDS_AVAILABLE) {
      const d = asQuantityConflict(e.data)
      // 用返回的最新余额刷新弹窗，而非只弹提示
      if (d) {
        planForm.orderQty = d.orderQty
        planForm.scheduledQty = d.scheduledQty
        planForm.availableQty = d.availableQty
      }
    }
    // 其余错误请求层已提示
  } finally {
    planSubmitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="toolbar">
        <span class="title">销售订单详情</span>
        <div>
          <el-button v-if="auth.hasPerm(PERM.plan.salesOrder.update) && detail?.actions.canEdit" @click="router.push(`/plan/sales-order/edit/${id}`)">编辑</el-button>
          <el-button
            v-if="auth.hasPerm(PERM.plan.salesOrder.create) && detail?.actions.canCreatePlan"
            type="primary" @click="openCreatePlan()"
          >创建计划</el-button>
        </div>
      </div>
    </template>

    <template v-if="detail">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="订单号">{{ detail.orderNo }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ detail.customerName }}</el-descriptions-item>
        <el-descriptions-item label="订单日期">{{ detail.orderDate }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag size="small">{{ SALES_ORDER_STATUS_LABEL[detail.status] }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.cancelledAt" label="取消原因" :span="3">{{ detail.cancelReason }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">订单明细</el-divider>
      <el-table :data="detail.items" border size="small">
        <el-table-column prop="lineNo" label="行号" width="70" align="center" />
        <el-table-column label="产品">
          <template #default="{ row }">
            <span>{{ (row as SalesOrderItem).productCode }} {{ (row as SalesOrderItem).productName }}</span>
            <el-tag v-if="(row as SalesOrderItem).productStatus === '1'" size="small" type="info" class="ml4">停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unitName" label="单位" width="80" />
        <el-table-column prop="orderQty" label="订单数量" width="120" align="right" />
        <el-table-column prop="scheduledQty" label="已排" width="110" align="right" />
        <el-table-column prop="availableQty" label="可排" width="110" align="right" />
        <el-table-column prop="completedQty" label="完成量" width="110" align="right" />
        <el-table-column prop="dueDate" label="交期" width="120" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-tooltip
              v-if="auth.hasPerm(PERM.plan.salesOrder.create)"
              :disabled="(row as SalesOrderItem).canCreatePlan"
              :content="reasonText((row as SalesOrderItem).disableReason)"
            >
              <span>
                <el-button
                  link type="primary" :disabled="!(row as SalesOrderItem).canCreatePlan"
                  @click="openCreatePlan(row as SalesOrderItem)"
                >创建计划</el-button>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-dialog v-model="planDialog" title="创建生产计划" width="560px">
      <el-form label-width="100px">
        <el-form-item label="订单行">
          <el-select :model-value="planForm.orderItemId" filterable placeholder="选择订单行" @change="onCandidateChange">
            <el-option
              v-for="c in candidates" :key="c.orderItemId" :value="c.orderItemId"
              :label="`${c.orderNo} 行${c.lineNo} ${c.productCode} ${c.productName}`"
              :disabled="!c.canCreatePlan"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="产品">{{ planForm.productName }}</el-form-item>
        <el-form-item label="数量信息">
          <span class="qty-info">
            订单 {{ planForm.orderQty }} · 已排 {{ planForm.scheduledQty }} · 可排 {{ planForm.availableQty }} {{ planForm.unitName }}
          </span>
        </el-form-item>
        <el-form-item label="计划数量">
          <el-input v-model="planForm.plannedQty" placeholder="十进制，如 4.0000" />
        </el-form-item>
        <el-form-item label="计划起止">
          <el-date-picker
            :model-value="[planForm.plannedStartAt, planForm.plannedEndAt]" type="datetimerange"
            @change="(v: Date[] | null) => { planForm.plannedStartAt = v?.[0]?.toISOString() ?? ''; planForm.plannedEndAt = v?.[1]?.toISOString() ?? '' }"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="planForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planDialog = false">取消</el-button>
        <el-button type="primary" :loading="planSubmitting" @click="submitPlan">提交</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; }
.ml4 { margin-left: 4px; }
.qty-info { color: var(--el-text-color-regular); }
</style>
