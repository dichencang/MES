<script setup lang="ts">
// 销售订单详情（契约-计划管理 §2.2）。展示逐行数量与能力；从行创建计划（拆分入口一）。
//  · 权限控显隐（auth.hasPerm）；业务能力控置灰（actions.canEdit/canCancel/canCreatePlan）+ disableReasons 原因
//  · 创建计划弹窗展示订单数量/已排/可排，提交由后端校验最新余额（超额 409 时刷新该行）
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSalesOrder, listOrderItems, createProductionPlan, cancelSalesOrder } from '@/api'
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

// ── 取消订单 ─────────────────────────────────────────
const canceling = ref(false)

async function cancelOrder() {
  if (!detail.value) return
  try {
    const { value } = await ElMessageBox.prompt(
      `确认取消订单「${detail.value.orderNo}」？请填写取消说明。`,
      '取消订单',
      {
        inputType: 'textarea', inputPlaceholder: '请输入取消原因（必填）',
        confirmButtonText: '确认取消', cancelButtonText: '返回',
        inputValidator: (v: string) => (v?.trim() ? true : '取消说明不能为空'),
      },
    )
    canceling.value = true
    await cancelSalesOrder(detail.value.id, { cancelReason: value.trim() })
    ElMessage.success('订单已取消')
    await load()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    // 409 + 4100：后端 message 已由请求层提示，这里只刷新最新能力状态
    if (e instanceof ApiError && e.code === 4100) { await load(); return }
    throw e
  } finally {
    canceling.value = false
  }
}

// ── 创建计划弹窗 ──────────────────────────────────────
const planDialog = ref(false)
const candidates = ref<OrderItemCandidate[]>([])
const planForm = reactive({
  orderItemId: '', orderNo: '', productName: '', unitName: '',
  orderQty: '', scheduledQty: '', availableQty: '',
  plannedQty: '', remark: null as string | null,
  /** el-date-picker datetimerange 的 v-model，值为 [Date, Date]；提交时转 ISO UTC Z */
  range: [] as Date[],
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
  planForm.range = []
  planForm.remark = null
}

function resetPlanForm() {
  fillPlanForm(null)
}

async function onCandidateChange(oid: string) {
  const c = candidates.value.find((x) => x.orderItemId === oid)
  if (c) fillPlanForm(c)
}

/** Date → ISO 8601 UTC Z（后端 parse_utc 要求 …Z；去掉毫秒更干净） */
function toUtcZ(d: Date): string {
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z')
}

async function submitPlan() {
  if (!planForm.orderItemId) { ElMessage.warning('请选择订单行'); return }
  if (!planForm.plannedQty || Number(planForm.plannedQty) <= 0) { ElMessage.warning('计划数量须大于 0'); return }
  const [start, end] = planForm.range
  if (!start || !end) { ElMessage.warning('请选择起止时间'); return }
  if (end <= start) { ElMessage.warning('结束时间须晚于开始时间'); return }
  const payload: PlanCreatePayload = {
    orderItemId: planForm.orderItemId,
    plannedQty: planForm.plannedQty,
    plannedStartAt: toUtcZ(start),
    plannedEndAt: toUtcZ(end),
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
        <div class="actions-bar">
          <el-tooltip
            v-if="auth.hasPerm(PERM.plan.salesOrder.update)"
            :disabled="detail?.actions.canEdit !== false"
            :content="reasonText(detail?.actions.disableReasons.edit)"
          >
            <span>
              <el-button
                :disabled="!detail?.actions.canEdit"
                @click="router.push(`/plan/sales-order/edit/${id}`)"
              >编辑</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.plan.salesOrder.create)"
            :disabled="detail?.actions.canCreatePlan !== false"
            :content="reasonText(detail?.actions.disableReasons.createPlan)"
          >
            <span>
              <el-button :disabled="!detail?.actions.canCreatePlan" type="primary" @click="openCreatePlan()">创建计划</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.plan.salesOrder.cancel)"
            :disabled="detail?.actions.canCancel !== false"
            :content="reasonText(detail?.actions.disableReasons.cancel)"
          >
            <span>
              <el-button :disabled="!detail?.actions.canCancel" type="danger" :loading="canceling" @click="cancelOrder()">取消</el-button>
            </span>
          </el-tooltip>
        </div>
      </div>
    </template>

    <template v-if="detail">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="订单号">{{ detail.orderNo }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ detail.customerName }}</el-descriptions-item>
        <el-descriptions-item label="订单日期">{{ detail.orderDate }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag size="small">{{ SALES_ORDER_STATUS_LABEL[detail.status] }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.cancelledAt" label="取消原因" :span="2">{{ detail.cancelReason }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">订单明细</el-divider>
      <!-- 明细列较多（含数量三态+完成量+交期），单位并入产品单元格，窄屏横向滚动兜底，避免丢列 -->
      <el-table :data="detail.items" border size="small" class="items-table">
        <el-table-column prop="lineNo" label="行号" width="60" align="center" />
        <el-table-column label="产品" min-width="170">
          <template #default="{ row }">
            <span>{{ (row as SalesOrderItem).productCode }} {{ (row as SalesOrderItem).productName }}</span>
            <el-tag v-if="(row as SalesOrderItem).productStatus === '1'" size="small" type="info" class="ml4">停用</el-tag>
            <div class="unit-hint">{{ (row as SalesOrderItem).unitName }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="orderQty" label="订单数量" width="100" align="right" />
        <el-table-column prop="scheduledQty" label="已排" width="95" align="right" />
        <el-table-column prop="availableQty" label="可排" width="95" align="right" />
        <el-table-column prop="completedQty" label="完成量" width="95" align="right" />
        <el-table-column prop="dueDate" label="交期" width="105" />
        <el-table-column label="操作" width="90" fixed="right">
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
            v-model="planForm.range" type="datetimerange"
            start-placeholder="开始时间" end-placeholder="结束时间"
            style="width: 100%"
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
.actions-bar { display: flex; gap: 8px; }
.title { font-weight: 600; }
.ml4 { margin-left: 4px; }
.qty-info { color: var(--el-text-color-regular); }
/* 明细列多，窄屏允许横向滚动，保证已排/可排/完成量/交期不被挤掉 */
.items-table { width: 100%; }
.unit-hint { font-size: 12px; color: var(--el-text-color-secondary); }
</style>
