<script setup lang="ts">
// 生产计划详情（契约-计划管理 §3.2）。转单入口由 features.workOrderTransferEnabled 控制：
//  · false → 不渲染（工单模块未交付）
//  · true + actions.canTransfer → 可点；禁用时置灰并提示 disableReason
// 重复转单按成功返回现有工单；缺版本 409 保留计划并提示；余额冲突/状态冲突按结构化 data 处理。
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getProductionPlan, transferProductionPlan, cancelProductionPlan } from '@/api'
import { ApiError } from '@/api/request'
import { BIZ_CODE, PLAN_BIZ_CODE } from '@/constants/biz'
import { PERM } from '@/constants/perm'
import { useAuthStore } from '@/stores/auth'
import {
  PLAN_STATUS_LABEL, type ProductionPlanDetail,
} from '@/types'
import { formatUtcShanghai } from '@/utils/time'
import {
  asMissingDefinition, asStateConflict, reasonText, showMissingDefinition,
} from '../components/feedback'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const detail = ref<ProductionPlanDetail | null>(null)
const transferring = ref(false)
const canceling = ref(false)
const id = computed(() => String(route.params.id))

async function load() {
  loading.value = true
  try {
    detail.value = await getProductionPlan(id.value)
  } finally {
    loading.value = false
  }
}

async function doTransfer() {
  transferring.value = true
  try {
    const res = await transferProductionPlan(id.value)
    ElMessage.success(res.workOrder ? `已转工单 ${res.workOrder.workOrderNo}` : '转单成功')
    await load()
  } catch (e) {
    if (e instanceof ApiError && e.code === PLAN_BIZ_CODE.MISSING_PRODUCTION_DEFINITION) {
      const d = asMissingDefinition(e.data)
      await showMissingDefinition(e.data, detail.value?.productName)
      // 提示后用户可去配置；d 用于将来可能的跳转定位
      void d
    } else if (e instanceof ApiError && e.code === PLAN_BIZ_CODE.STATE_CONFLICT) {
      const r = asStateConflict(e.data)
      await ElMessageBox.alert(reasonText(r), '无法转单', { type: 'warning' })
    }
    // 其余错误请求层已提示
  } finally {
    transferring.value = false
  }
}

async function doCancel() {
  try {
    const { value } = await ElMessageBox.prompt(
      `确认取消计划「${detail.value?.planNo}」？请填写取消说明。`, '取消计划',
      {
        inputType: 'textarea', inputPlaceholder: '请输入取消原因（必填）',
        confirmButtonText: '确认取消', cancelButtonText: '返回',
        inputValidator: (v: string) => (v?.trim() ? true : '取消说明不能为空'),
      },
    )
    canceling.value = true
    await cancelProductionPlan(id.value, { cancelReason: value.trim() })
    ElMessage.success('计划已取消')
    await load()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    if (e instanceof ApiError && e.code === BIZ_CODE.INVALID_PARAM) return
    if (e instanceof ApiError && e.code === PLAN_BIZ_CODE.STATE_CONFLICT) {
      const r = asStateConflict(e.data)
      await ElMessageBox.alert(reasonText(r), '无法取消', { type: 'warning' })
    }
  } finally {
    canceling.value = false
  }
}
onMounted(load)
</script>

<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="toolbar">
        <span class="title">生产计划详情</span>
        <div class="actions-bar">
          <el-tooltip
            v-if="auth.hasPerm(PERM.plan.productionPlan.update)"
            :disabled="detail?.actions.canReschedule !== false"
            :content="reasonText(detail?.actions.disableReasons.reschedule)"
          >
            <span>
              <el-button
                :disabled="!detail?.actions.canReschedule"
                @click="router.push(`/plan/production-plan/edit/${id}`)"
              >编辑排期</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.plan.productionPlan.cancel)"
            :disabled="detail?.actions.canCancel !== false"
            :content="reasonText(detail?.actions.disableReasons.cancel)"
          >
            <span>
              <el-button :disabled="!detail?.actions.canCancel" type="danger" :loading="canceling" @click="doCancel">取消</el-button>
            </span>
          </el-tooltip>
          <el-tooltip
            v-if="auth.hasPerm(PERM.plan.productionPlan.transfer) && detail?.features.workOrderTransferEnabled"
            :disabled="detail?.actions.canTransfer !== false"
            :content="reasonText(detail?.actions.disableReasons.transfer)"
          >
            <span>
              <el-button
                type="primary" :disabled="!detail?.actions.canTransfer" :loading="transferring"
                @click="doTransfer"
              >转工单</el-button>
            </span>
          </el-tooltip>
        </div>
      </div>
    </template>

    <template v-if="detail">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="计划号">{{ detail.planNo }}</el-descriptions-item>
        <el-descriptions-item label="订单号">{{ detail.orderNo }}</el-descriptions-item>
        <el-descriptions-item label="产品">{{ detail.productCode }} {{ detail.productName }}</el-descriptions-item>
        <el-descriptions-item label="单位">{{ detail.unitCode }} {{ detail.unitName }}</el-descriptions-item>
        <el-descriptions-item label="计划数量">{{ detail.plannedQty }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag size="small">{{ PLAN_STATUS_LABEL[detail.status] }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatUtcShanghai(detail.plannedStartAt) }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ formatUtcShanghai(detail.plannedEndAt) }}</el-descriptions-item>
        <el-descriptions-item label="BOM 版本">{{ detail.bomVersion ? `V${detail.bomVersion.version}` : '—' }}</el-descriptions-item>
        <el-descriptions-item label="路线版本">{{ detail.routingVersion ? `V${detail.routingVersion.version}` : '—' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
        <el-descriptions-item v-if="detail.cancelledAt" label="取消原因" :span="2">{{ detail.cancelReason }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">关联工单</el-divider>
      <div v-if="detail.workOrder" class="workorder">
        <span>工单 {{ detail.workOrder.workOrderNo }}</span>
        <el-button
          link type="primary"
          @click="router.push(`/workorder/detail/${detail.workOrder.id}`)"
        >查看工单</el-button>
      </div>
      <el-empty v-else description="暂无关联工单" :image-size="60" />
    </template>
  </el-card>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.actions-bar { display: flex; gap: 8px; }
.title { font-weight: 600; }
.workorder { display: flex; align-items: center; gap: 12px; }
</style>
