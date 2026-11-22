<script setup lang="ts">
// 工单详情（契约-生产工单 §二/§三/§四）。
//  · 动作全部由「权限控显隐 + actions 控置灰 + disableReasons 作 tooltip」驱动
//  · 派工在详情内（抽屉）：整步全量替换，空数组＝取消预派
//  · 完成/关闭本期无写接口：按钮显示但恒置灰，原因 WORK_ORDER_SETTLEMENT_DISABLED
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  cancelWorkOrder, getWorkOrder, listAssigneeOptions, listWorkOrderEvents,
  releaseWorkOrder, setStepAssignees, startWorkOrder,
} from '@/api'
import { BIZ_CODE } from '@/constants/biz'
import { PERM } from '@/constants/perm'
import { useAuthStore } from '@/stores/auth'
import {
  WO_EVENT_LABEL, WO_STATUS_LABEL,
  type AssigneeOption, type WorkOrderDetail, type WorkOrderEvent,
  type WorkOrderMaterial, type WorkOrderStatus, type WorkOrderStep,
} from '@/types'
import { formatUtcShanghai } from '@/utils/time'
import { ApiError, paramError, reasonText } from './components/feedback'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const id = computed(() => String(route.params.id))
const loading = ref(true)
const detail = ref<WorkOrderDetail | null>(null)
const acting = ref(false)

async function load() {
  loading.value = true
  try {
    detail.value = await getWorkOrder(id.value)
  } finally {
    loading.value = false
  }
}

function statusType(s: WorkOrderStatus): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  if (s === 'IN_PRODUCTION') return 'primary'
  if (s === 'COMPLETED') return 'success'
  if (s === 'CANCELLED' || s === 'CLOSED') return 'info'
  if (s === 'RELEASED') return 'warning'
  return 'danger'
}

/** 动作统一收口：成功后就地刷新详情，失败交给请求层与结构化提示 */
async function runAction(fn: () => Promise<WorkOrderDetail>, successText: string) {
  acting.value = true
  try {
    detail.value = await fn()
    ElMessage.success(successText)
  } catch (e) {
    if (e instanceof ApiError && e.code === 4100) {
      const reason = (e.data as { reason?: { code: string; message: string } } | undefined)?.reason
      if (reason) await ElMessageBox.alert(reasonText(reason), '操作未完成', { type: 'warning' })
      await load()
    }
  } finally {
    acting.value = false
  }
}

async function doRelease() {
  await ElMessageBox.confirm('确认下发该工单？下发后数量、排期与生产定义将被冻结。', '下发工单', {
    type: 'warning', confirmButtonText: '确认下发', cancelButtonText: '返回',
  })
  await runAction(() => releaseWorkOrder(id.value), '工单已下发')
}

async function doStart() {
  await ElMessageBox.confirm('确认开始生产？将记录实际开工时间。', '开工', {
    type: 'warning', confirmButtonText: '确认开工', cancelButtonText: '返回',
  })
  await runAction(() => startWorkOrder(id.value), '已开工')
}

async function doCancel() {
  const { value } = await ElMessageBox.prompt('请填写撤销原因（必填，最多 200 字）', '撤销工单', {
    inputType: 'textarea', inputPlaceholder: '撤销原因',
    confirmButtonText: '确认撤销', cancelButtonText: '返回',
    inputValidator: (v: string) => {
      const t = (v ?? '').trim()
      if (!t) return '撤销原因不能为空'
      if (t.length > 200) return '最多 200 个字符'
      return true
    },
  })
  await runAction(() => cancelWorkOrder(id.value, { cancelReason: value.trim() }), '工单已撤销')
}

// ── 派工抽屉（整步全量替换）────────────────────────────
const assignDrawer = ref(false)
const assignStep = ref<WorkOrderStep | null>(null)
const assignIds = ref<string[]>([])
const assignOptions = ref<AssigneeOption[]>([])
const assignLoading = ref(false)
const assigning = ref(false)

async function loadAssignees(keyword: string) {
  assignLoading.value = true
  try {
    const res = await listAssigneeOptions({ keyword: keyword || undefined, pageSize: 20 })
    assignOptions.value = res.list
  } finally {
    assignLoading.value = false
  }
}

function openAssign(step: WorkOrderStep) {
  assignStep.value = step
  // 当前有效分配（endedAt 为 null）预选
  assignIds.value = step.assignees.filter((a) => !a.endedAt).map((a) => a.assigneeId)
  assignDrawer.value = true
  loadAssignees('')
  // 已选但不在候选里的历史人员补进候选，避免回显丢失
  for (const a of step.assignees.filter((x) => !x.endedAt)) {
    if (!assignOptions.value.some((o) => o.id === a.assigneeId)) {
      assignOptions.value.unshift({ id: a.assigneeId, username: a.assigneeName, realName: a.assigneeName })
    }
  }
}

async function submitAssign() {
  if (!assignStep.value) return
  assigning.value = true
  try {
    detail.value = await setStepAssignees(id.value, assignStep.value.id, { assigneeIds: assignIds.value })
    ElMessage.success('派工已更新')
    assignDrawer.value = false
  } catch (e) {
    if (e instanceof ApiError && e.code === BIZ_CODE.INVALID_PARAM) {
      ElMessage.warning(paramError(e.data, 'assigneeIds'))
      return
    }
    if (e instanceof ApiError && e.code === 4100) {
      const reason = (e.data as { reason?: { code: string; message: string } } | undefined)?.reason
      if (reason) ElMessage.warning(reasonText(reason))
      await load()
    }
  } finally {
    assigning.value = false
  }
}

/** 工序当前派工文案 */
function currentAssignees(step: WorkOrderStep): string {
  const cur = step.assignees.filter((a) => !a.endedAt).map((a) => a.assigneeName)
  return cur.length ? cur.join('、') : '未派工'
}

// ── 事件时间线（内嵌最近 10 条 + 抽屉分页）─────────────
const eventsDrawer = ref(false)
const eventsLoading = ref(false)
const eventsList = ref<WorkOrderEvent[]>([])
const eventsQuery = reactive({ page: 1, pageSize: 10 })
const eventsTotal = ref(0)

function openEvents() {
  eventsDrawer.value = true
  eventsQuery.page = 1
  loadEvents()
}

async function loadEvents() {
  eventsLoading.value = true
  try {
    const res = await listWorkOrderEvents(id.value, { page: eventsQuery.page, pageSize: eventsQuery.pageSize })
    eventsList.value = res.list
    eventsTotal.value = res.total
  } finally {
    eventsLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="toolbar">
        <span class="title">工单详情</span>
        <div class="actions-bar">
          <el-tooltip
            v-if="auth.hasPerm(PERM.workorder.update)"
            :disabled="detail?.actions.canEdit !== false"
            :content="reasonText(detail?.actions.disableReasons.edit)"
          >
            <span>
              <el-button
                :disabled="!detail?.actions.canEdit"
                @click="router.push(`/workorder/edit/${id}`)"
              >编辑</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.workorder.release)"
            :disabled="detail?.actions.canRelease !== false"
            :content="reasonText(detail?.actions.disableReasons.release)"
          >
            <span>
              <el-button :disabled="!detail?.actions.canRelease" :loading="acting" @click="doRelease">下发</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.workorder.start)"
            :disabled="detail?.actions.canStart !== false"
            :content="reasonText(detail?.actions.disableReasons.start)"
          >
            <span>
              <el-button :disabled="!detail?.actions.canStart" type="primary" :loading="acting" @click="doStart">开工</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.workorder.cancel)"
            :disabled="detail?.actions.canCancel !== false"
            :content="reasonText(detail?.actions.disableReasons.cancel)"
          >
            <span>
              <el-button :disabled="!detail?.actions.canCancel" type="danger" :loading="acting" @click="doCancel">撤销</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.workorder.complete)"
            :disabled="detail?.actions.canComplete !== false"
            :content="reasonText(detail?.actions.disableReasons.complete)"
          >
            <span><el-button :disabled="!detail?.actions.canComplete">完工</el-button></span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.workorder.close)"
            :disabled="detail?.actions.canClose !== false"
            :content="reasonText(detail?.actions.disableReasons.close)"
          >
            <span><el-button :disabled="!detail?.actions.canClose">关闭</el-button></span>
          </el-tooltip>
        </div>
      </div>
    </template>

    <template v-if="detail">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="工单号">{{ detail.workOrderNo }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag size="small" :type="statusType(detail.status)">{{ WO_STATUS_LABEL[detail.status] }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="产品">
          {{ detail.productCode }} {{ detail.productName }}
          <span class="unit-hint">{{ detail.unitName }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ detail.plannedQty }}</el-descriptions-item>
        <el-descriptions-item label="计划开始">{{ formatUtcShanghai(detail.plannedStartAt) }}</el-descriptions-item>
        <el-descriptions-item label="计划结束">{{ formatUtcShanghai(detail.plannedEndAt) }}</el-descriptions-item>
        <el-descriptions-item label="来源计划">
          <el-button v-if="detail.planId" link type="primary" @click="router.push(`/plan/production-plan/view/${detail.planId}`)">
            {{ detail.planNo }}
          </el-button>
          <span v-else>—（手工工单）</span>
        </el-descriptions-item>
        <el-descriptions-item label="BOM / 路线版本">
          {{ detail.bomVersion ? `v${detail.bomVersion.version}` : '—' }} /
          {{ detail.routingVersion ? `v${detail.routingVersion.version}` : '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="下发 / 开工">
          {{ detail.releasedAt ? formatUtcShanghai(detail.releasedAt) : '未下发' }} /
          {{ detail.startedAt ? formatUtcShanghai(detail.startedAt) : '未开工' }}
        </el-descriptions-item>
        <el-descriptions-item label="备注">{{ detail.remark || '—' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.cancelledAt" label="撤销原因" :span="2">
          {{ detail.cancelReason }}（{{ formatUtcShanghai(detail.cancelledAt) }}）
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">工单用料（直接子件）</el-divider>
      <el-table :data="detail.materials" border size="small">
        <el-table-column prop="sortNo" label="序" width="50" align="center" />
        <el-table-column label="物料" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ (row as WorkOrderMaterial).materialCode }} {{ (row as WorkOrderMaterial).materialName }}
            <span class="unit-hint">{{ (row as WorkOrderMaterial).unitName }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="baseQty" label="基准量" width="85" align="right" />
        <el-table-column prop="componentQty" label="单位用量" width="90" align="right" />
        <el-table-column prop="requiredQty" label="需求量" width="85" align="right" />
      </el-table>

      <el-divider content-position="left">工序与派工</el-divider>
      <el-table :data="detail.steps" border size="small">
        <el-table-column prop="seq" label="序" width="50" align="center" />
        <el-table-column label="工序" min-width="130">
          <template #default="{ row }">
            {{ (row as WorkOrderStep).processCode }} {{ (row as WorkOrderStep).processName }}
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="90" show-overflow-tooltip>
          <template #default="{ row }">{{ (row as WorkOrderStep).remark || '—' }}</template>
        </el-table-column>
        <el-table-column label="当前派工" min-width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ currentAssignees(row as WorkOrderStep) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{ row }">
            <el-tooltip
              :disabled="(row as WorkOrderStep).canAssign"
              :content="reasonText((row as WorkOrderStep).disableReason)"
            >
              <span>
                <el-button
                  v-if="auth.hasPerm(PERM.workorder.assign)"
                  link type="primary" :disabled="!(row as WorkOrderStep).canAssign"
                  @click="openAssign(row as WorkOrderStep)"
                >派工</el-button>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <el-divider content-position="left">执行时间线</el-divider>
      <el-timeline v-if="detail.events.length">
        <el-timeline-item
          v-for="e in detail.events" :key="e.id"
          :timestamp="formatUtcShanghai(e.occurredAt)" placement="top"
        >
          <div class="event-line">
            <strong>{{ WO_EVENT_LABEL[e.action] ?? e.action }}</strong>
            <span class="event-status">
              {{ e.fromStatus ? WO_STATUS_LABEL[e.fromStatus] : '—' }} → {{ WO_STATUS_LABEL[e.toStatus] }}
            </span>
            <span class="event-op">{{ e.operatorName }}</span>
            <span v-if="e.reason" class="event-reason">原因：{{ e.reason }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无事件" :image-size="60" />
      <el-button v-if="detail.events.length" link type="primary" @click="openEvents">查看全部事件</el-button>
    </template>

    <!-- 派工抽屉：整步全量替换 -->
    <el-drawer v-model="assignDrawer" title="工序派工" size="420px">
      <div v-if="assignStep" class="assign-body">
        <el-alert
          type="info" :closable="false" show-icon class="mb"
          :title="`${assignStep.processCode} ${assignStep.processName}`"
          description="为该工序选择一个或多个员工；清空后保存即取消预派。"
        />
        <el-select
          v-model="assignIds" multiple filterable remote clearable
          :remote-method="loadAssignees" :loading="assignLoading"
          placeholder="搜索账号或姓名" class="assign-select"
        >
          <el-option
            v-for="o in assignOptions" :key="o.id" :value="o.id"
            :label="`${o.realName}（${o.username}）`"
          />
        </el-select>
        <div v-if="assignStep.assignees.some(a => a.endedAt)" class="history">
          <div class="history-title">历史分配</div>
          <div v-for="a in assignStep.assignees.filter(x => x.endedAt)" :key="a.id" class="history-item">
            {{ a.assigneeName }} · {{ formatUtcShanghai(a.assignedAt) }} → {{ formatUtcShanghai(a.endedAt) }}
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="assignDrawer = false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="submitAssign">保存</el-button>
      </template>
    </el-drawer>

    <!-- 全部事件 -->
    <el-drawer v-model="eventsDrawer" title="全部事件" size="520px">
      <div v-loading="eventsLoading">
        <el-timeline v-if="eventsList.length">
          <el-timeline-item
            v-for="e in eventsList" :key="e.id"
            :timestamp="formatUtcShanghai(e.occurredAt)" placement="top"
          >
            <div class="event-line">
              <strong>{{ WO_EVENT_LABEL[e.action] ?? e.action }}</strong>
              <span class="event-status">
                {{ e.fromStatus ? WO_STATUS_LABEL[e.fromStatus] : '—' }} → {{ WO_STATUS_LABEL[e.toStatus] }}
              </span>
              <span class="event-op">{{ e.operatorName }}</span>
              <span v-if="e.reason" class="event-reason">原因：{{ e.reason }}</span>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-pagination
          v-if="eventsTotal > eventsQuery.pageSize"
          class="pager"
          :current-page="eventsQuery.page"
          :page-size="eventsQuery.pageSize"
          :total="eventsTotal"
          layout="total, prev, pager, next"
          @current-change="(p: number) => { eventsQuery.page = p; loadEvents() }"
        />
      </div>
    </el-drawer>
  </el-card>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.actions-bar { display: flex; gap: 8px; flex-wrap: wrap; }
.title { font-weight: 600; white-space: nowrap; }
.unit-hint { margin-left: 4px; font-size: 12px; color: var(--el-text-color-secondary); }
.event-line { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; font-size: 13px; }
.event-status { color: var(--el-text-color-secondary); }
.event-op { color: var(--el-text-color-secondary); }
.event-reason { color: var(--el-color-warning); }
.assign-body { display: flex; flex-direction: column; gap: 14px; }
.assign-select { width: 100%; }
.mb { margin-bottom: 4px; }
.history-title { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 6px; }
.history-item { font-size: 12px; color: var(--el-text-color-regular); line-height: 1.8; }
.pager { margin-top: 12px; }
</style>
