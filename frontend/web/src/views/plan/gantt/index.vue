<script setup lang="ts">
// 计划甘特图（契约-计划管理 §4）。GET /plan/gantt，dateStart/dateEnd 必填含首尾，
// 点击条目进计划详情，首期只读（时间调整在详情表单）。用原生 Date 计算按天刻度，不引入第三方库。
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listGantt, materialOptions } from '@/api'
import { ApiError } from '@/api/request'
import type { GanttPlan, MaterialOption } from '@/types'
import { formatUtcShanghai } from '@/utils/time'
import { ganttDateError } from '../components/feedback'

const router = useRouter()
const loading = ref(false)
const plans = ref<GanttPlan[]>([])
const productOptions = ref<MaterialOption[]>([])
const errors = ref<string[]>([])

const DAY = 24 * 3600 * 1000
// 契约 §4.3（v1.1）：单次查询最多 92 个自然日（含首尾），最多 2000 条；超限后端 400+1001
const MAX_DAYS = 92

function today() { return new Date().toISOString().slice(0, 10) }
function shift(dateStr: string, days: number): string {
  return new Date(new Date(dateStr + 'T00:00:00Z').getTime() + days * DAY).toISOString().slice(0, 10)
}
/** 含首尾的自然日跨度 */
function spanDays(start: string, end: string): number {
  if (!start || !end) return 0
  return Math.floor((new Date(end + 'T00:00:00Z').getTime() - new Date(start + 'T00:00:00Z').getTime()) / DAY) + 1
}

const query = reactive({
  dateStart: shift(today(), -7),
  dateEnd: shift(today(), 30),
  productId: '',
})

const days = computed<string[]>(() => {
  const out: string[] = []
  let cur = query.dateStart
  // 上限 92 天，防止误选超长区间撑爆 DOM
  for (let i = 0; i < MAX_DAYS && cur <= query.dateEnd; i++) {
    out.push(cur)
    cur = shift(cur, 1)
  }
  return out
})

const truncated = computed(() => days.value.length >= MAX_DAYS && shift(days.value[MAX_DAYS - 1] ?? query.dateStart, 1) <= query.dateEnd)
/** 当前选择是否超过 92 天（超限不发请求，直接提示） */
const spanTooLong = computed(() => spanDays(query.dateStart, query.dateEnd) > MAX_DAYS)

function ratio(dateStr: string): number {
  // UTC Z → 上海日期，再落到区间刻度
  const shanghaiDate = formatUtcShanghai(dateStr).slice(0, 10)
  const start = new Date(query.dateStart + 'T00:00:00Z').getTime()
  const cur = new Date(shanghaiDate + 'T00:00:00Z').getTime()
  const span = Math.max(days.value.length - 1, 1) * DAY
  return Math.min(Math.max((cur - start) / span, 0), 1)
}

function barStyle(p: GanttPlan) {
  const left = ratio(p.startAt)
  // 结束按上海日期的次日零点算宽度，至少一格
  const endRatio = ratio(p.endAt)
  const width = Math.max(endRatio - left + 1 / Math.max(days.value.length, 1), 1 / Math.max(days.value.length, 1))
  return { left: `${left * 100}%`, width: `${Math.min(width, 1 - left) * 100}%` }
}

async function load() {
  errors.value = []
  if (!query.dateStart || !query.dateEnd) {
    errors.value = ['请选择开始日和结束日']
    return
  }
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
    plans.value = await listGantt(params)
  } catch (e) {
    if (e instanceof ApiError && e.code === 1001) {
      // 含条数超 2000 的拒绝：后端在 data.errors 的 dateEnd 字段给出提示
      const msg = ganttDateError(e.data)
      errors.value = [msg]
      ElMessage.error(msg)
    }
    plans.value = []
  } finally {
    loading.value = false
  }
}

async function loadProducts(keyword: string) {
  const res = await materialOptions({ keyword, isProduct: true, pageSize: 20 })
  productOptions.value = res.list
}

onMounted(() => { load(); loadProducts('') })
</script>

<template>
  <el-card v-loading="loading">
    <template #header><span class="title">计划甘特图</span></template>

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
      <el-tag v-for="v in ['PENDING_TRANSFER', 'TRANSFERRED', 'CANCELLED']" :key="v" size="small" :type="v === 'TRANSFERRED' ? 'success' : v === 'CANCELLED' ? 'info' : 'warning'">
        {{ v === 'PENDING_TRANSFER' ? '待转单' : v === 'TRANSFERRED' ? '已转单' : '已取消' }}
      </el-tag>
      <span v-if="truncated" class="warn">区间超过 92 天，仅展示前 92 天</span>
    </div>

    <div class="gantt">
      <div class="gantt-head">
        <div class="gantt-label">计划 / 订单</div>
        <div class="gantt-track">
          <div v-for="d in days" :key="d" class="gantt-day">{{ d.slice(5) }}</div>
        </div>
      </div>
      <div v-for="p in plans" :key="p.planId" class="gantt-row" @click="router.push(`/plan/production-plan/view/${p.planId}`)">
        <div class="gantt-label">
          <div class="gantt-plan-no">{{ p.planNo }}</div>
          <div class="gantt-sub">{{ p.orderNo }} · {{ p.productName }}</div>
        </div>
        <div class="gantt-track">
          <div class="gantt-bar" :class="`gantt-bar--${p.status}`" :style="barStyle(p)">
            <span>{{ formatUtcShanghai(p.startAt) }} → {{ formatUtcShanghai(p.endAt) }}</span>
          </div>
        </div>
      </div>
      <el-empty v-if="!plans.length && !loading" description="区间内暂无计划" :image-size="70" />
    </div>
  </el-card>
</template>

<style scoped>
.title { font-weight: 600; }
.search :deep(.el-date-editor), .search :deep(.el-select) { width: 180px; }
.mb { margin-bottom: 12px; }
.limit-hint { margin-left: 10px; font-size: 12px; color: var(--el-text-color-secondary); }
.hints { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
.warn { color: var(--el-color-warning); font-size: 12px; }
.gantt { border: 1px solid var(--el-border-color); border-radius: 4px; overflow-x: auto; }
.gantt-head, .gantt-row { display: flex; min-width: 900px; }
.gantt-head { background: var(--el-fill-color-light); font-size: 12px; color: var(--el-text-color-secondary); }
.gantt-row { border-top: 1px solid var(--el-border-color-lighter); cursor: pointer; }
.gantt-row:hover { background: var(--el-fill-color-lighter); }
.gantt-label { width: 200px; flex: 0 0 200px; padding: 8px 10px; border-right: 1px solid var(--el-border-color-lighter); }
.gantt-plan-no { font-weight: 500; }
.gantt-sub { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }
.gantt-track { position: relative; flex: 1; display: flex; min-width: 700px; }
.gantt-day { flex: 1; text-align: center; padding: 8px 0; border-right: 1px solid var(--el-border-color-lighter); }
.gantt-row .gantt-track { min-height: 44px; align-items: center; }
.gantt-bar {
  position: absolute; top: 8px; bottom: 8px; border-radius: 4px; padding: 0 6px;
  display: flex; align-items: center; font-size: 11px; color: #fff; overflow: hidden; white-space: nowrap;
}
.gantt-bar--PENDING_TRANSFER { background: var(--el-color-warning); }
.gantt-bar--TRANSFERRED { background: var(--el-color-success); }
.gantt-bar--CANCELLED { background: var(--el-color-info); opacity: .7; }
</style>
