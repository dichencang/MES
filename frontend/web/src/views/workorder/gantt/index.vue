<script setup lang="ts">
// 工单甘特图（契约-生产工单 §二 11）。GET /workorders/gantt，按排期重叠查询，
// 点击条目进工单详情；只看不排（排期在工单编辑页）。上限与计划甘特同口径：92 自然日 / 2000 条。
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listWorkOrderGantt, materialOptions } from '@/api'
import { ApiError } from '@/api/request'
import { BIZ_CODE } from '@/constants/biz'
import { WO_STATUS_LABEL, type GanttWorkOrder, type MaterialOption } from '@/types'
import { formatUtcShanghai } from '@/utils/time'
import { paramError } from '../components/feedback'

const router = useRouter()
const loading = ref(false)
const rows = ref<GanttWorkOrder[]>([])
const errors = ref<string[]>([])
const productOptions = ref<MaterialOption[]>([])

const DAY = 24 * 3600 * 1000
const MAX_DAYS = 92

function today() { return new Date().toISOString().slice(0, 10) }
function shift(dateStr: string, days: number): string {
  return new Date(new Date(dateStr + 'T00:00:00Z').getTime() + days * DAY).toISOString().slice(0, 10)
}
function spanDays(start: string, end: string): number {
  if (!start || !end) return 0
  return Math.floor((new Date(end + 'T00:00:00Z').getTime() - new Date(start + 'T00:00:00Z').getTime()) / DAY) + 1
}

const query = reactive({ dateStart: shift(today(), -7), dateEnd: shift(today(), 30), productId: '' })

const days = computed<string[]>(() => {
  const out: string[] = []
  let cur = query.dateStart
  for (let i = 0; i < MAX_DAYS && cur <= query.dateEnd; i++) {
    out.push(cur)
    cur = shift(cur, 1)
  }
  return out
})
const spanTooLong = computed(() => spanDays(query.dateStart, query.dateEnd) > MAX_DAYS)

function ratio(iso: string): number {
  const d = formatUtcShanghai(iso).slice(0, 10)
  const start = new Date(query.dateStart + 'T00:00:00Z').getTime()
  const cur = new Date(d + 'T00:00:00Z').getTime()
  const span = Math.max(days.value.length - 1, 1) * DAY
  return Math.min(Math.max((cur - start) / span, 0), 1)
}

function barStyle(w: GanttWorkOrder) {
  const left = ratio(w.plannedStartAt)
  const right = ratio(w.plannedEndAt)
  const unit = 1 / Math.max(days.value.length, 1)
  const width = Math.max(right - left + unit, unit)
  return { left: `${left * 100}%`, width: `${Math.min(width, 1 - left) * 100}%` }
}

async function load() {
  errors.value = []
  if (!query.dateStart || !query.dateEnd) { errors.value = ['请选择开始日和结束日']; return }
  if (spanTooLong.value) {
    const msg = `单次查询最多包含 ${MAX_DAYS} 个自然日（当前 ${spanDays(query.dateStart, query.dateEnd)} 天），请缩短日期范围`
    errors.value = [msg]
    ElMessage.error(msg)
    return
  }
  loading.value = true
  try {
    const params: Record<string, unknown> = { dateStart: query.dateStart, dateEnd: query.dateEnd }
    if (query.productId) params.productId = query.productId
    rows.value = await listWorkOrderGantt(params)
  } catch (e) {
    if (e instanceof ApiError && e.code === BIZ_CODE.INVALID_PARAM) {
      const msg = paramError(e.data, 'dateEnd')
      errors.value = [msg]
      ElMessage.error(msg)
    }
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function loadProducts(keyword: string) {
  const res = await materialOptions({ keyword: keyword || undefined, isProduct: true, pageSize: 20 })
  productOptions.value = res.list
}

onMounted(() => { load(); loadProducts('') })
</script>

<template>
  <el-card v-loading="loading">
    <template #header><span class="title">工单甘特图</span></template>

    <el-form :inline="true" class="search">
      <el-form-item label="起始日">
        <el-date-picker v-model="query.dateStart" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="结束日">
        <el-date-picker v-model="query.dateEnd" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="产品">
        <el-select v-model="query.productId" filterable remote clearable :remote-method="loadProducts" placeholder="全部产品">
          <el-option v-for="p in productOptions" :key="p.id" :value="p.id" :label="`${p.code} ${p.name}`" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="load">查询</el-button>
        <span class="limit-hint">单次最多 92 天、2000 条（当前 {{ spanDays(query.dateStart, query.dateEnd) }} 天）</span>
      </el-form-item>
    </el-form>

    <el-alert v-if="errors.length" :title="errors.join('；')" type="error" :closable="false" class="mb" />

    <div class="hints">
      <el-tag v-for="s in ['PENDING_RELEASE', 'RELEASED', 'IN_PRODUCTION', 'CANCELLED']" :key="s" size="small">
        {{ WO_STATUS_LABEL[s as keyof typeof WO_STATUS_LABEL] }}
      </el-tag>
    </div>

    <div class="gantt">
      <div class="gantt-head">
        <div class="gantt-label">工单 / 产品</div>
        <div class="gantt-track">
          <div v-for="d in days" :key="d" class="gantt-day">{{ d.slice(5) }}</div>
        </div>
      </div>
      <div v-for="w in rows" :key="w.id" class="gantt-row" @click="router.push(`/workorder/detail/${w.id}`)">
        <div class="gantt-label">
          <div class="gantt-no">{{ w.workOrderNo }}</div>
          <div class="gantt-sub">{{ w.productName }}<span v-if="w.planNo"> · {{ w.planNo }}</span></div>
        </div>
        <div class="gantt-track">
          <div class="gantt-bar" :class="`gantt-bar--${w.status}`" :style="barStyle(w)">
            <span>{{ formatUtcShanghai(w.plannedStartAt) }} → {{ formatUtcShanghai(w.plannedEndAt) }}</span>
          </div>
        </div>
      </div>
      <el-empty v-if="!rows.length && !loading" description="区间内暂无工单" :image-size="70" />
    </div>
  </el-card>
</template>

<style scoped>
.title { font-weight: 600; }
.search :deep(.el-date-editor), .search :deep(.el-select) { width: 180px; }
.limit-hint { margin-left: 10px; font-size: 12px; color: var(--el-text-color-secondary); }
.mb { margin-bottom: 12px; }
.hints { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
.gantt { border: 1px solid var(--el-border-color); border-radius: 4px; overflow-x: auto; }
.gantt-head, .gantt-row { display: flex; min-width: 900px; }
.gantt-head { background: var(--el-fill-color-light); font-size: 12px; color: var(--el-text-color-secondary); }
.gantt-row { border-top: 1px solid var(--el-border-color-lighter); cursor: pointer; }
.gantt-row:hover { background: var(--el-fill-color-lighter); }
.gantt-label { width: 200px; flex: 0 0 200px; padding: 8px 10px; border-right: 1px solid var(--el-border-color-lighter); }
.gantt-track { position: relative; flex: 1; display: flex; }
.gantt-no { font-weight: 500; }
.gantt-sub { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }
.gantt-day { flex: 1; text-align: center; padding: 8px 0; border-right: 1px solid var(--el-border-color-lighter); }
.gantt-row .gantt-track { min-height: 44px; align-items: center; }
.gantt-bar {
  position: absolute; top: 8px; bottom: 8px; border-radius: 4px; padding: 0 6px;
  display: flex; align-items: center; font-size: 11px; color: #fff; overflow: hidden; white-space: nowrap;
}
.gantt-bar--PENDING_RELEASE { background: var(--el-color-warning); }
.gantt-bar--RELEASED { background: var(--el-color-primary); }
.gantt-bar--IN_PRODUCTION { background: var(--el-color-success); }
.gantt-bar--COMPLETED { background: var(--el-color-success); opacity: .8; }
.gantt-bar--CLOSED { background: var(--el-color-info); opacity: .8; }
.gantt-bar--CANCELLED { background: var(--el-color-info); opacity: .6; }
</style>
