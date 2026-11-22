<script setup lang="ts">
// 工单新建 / 编辑（契约-生产工单 §二 3/4、§四）。
//  · 新建：选成品 + 数量 + 计划起止，提交后跳详情（后端展开用料与工序）
//  · 编辑：仅手工单待下发可进（权限 workorder:update + actions.canEdit），产品与绑定版本固定
//  · 数量为十进制字符串，前端只校验 >0 与四位小数，不做算术
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { createWorkOrder, getWorkOrder, materialOptions, updateWorkOrder } from '@/api'
import { BIZ_CODE, WORK_ORDER_BIZ_CODE } from '@/constants/biz'
import type { MaterialOption, WorkOrderDetail } from '@/types'
import { ApiError, paramError, showMissingDefinition, showQuantityInvalid } from './components/feedback'

const route = useRoute()
const router = useRouter()
const editing = computed(() => Boolean(route.params.id))
const formRef = ref<FormInstance>()
const submitting = ref(false)
const loading = ref(false)

const form = reactive({
  productId: '',
  productLabel: '',
  plannedQty: '',
  remark: null as string | null,
  /** el-date-picker datetimerange 的 v-model；提交时转 ISO UTC Z */
  range: [] as Date[],
})

const rules: FormRules = {
  plannedQty: [{ required: true, message: '请输入计划数量', trigger: 'blur' }],
}

const productOptions = ref<MaterialOption[]>([])
const productLoading = ref(false)
async function searchProduct(keyword: string) {
  productLoading.value = true
  try {
    const res = await materialOptions({ keyword: keyword || undefined, isProduct: true, pageSize: 20 })
    productOptions.value = res.list
  } finally {
    productLoading.value = false
  }
}

/** ISO UTC Z → Date（datetime picker 用） */
function toDate(iso: string | null): Date | null {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}
/** Date → ISO UTC Z（去掉毫秒） */
function toIso(d: Date): string {
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z')
}

async function loadDetail() {
  loading.value = true
  try {
    const d: WorkOrderDetail = await getWorkOrder(String(route.params.id))
    form.productId = d.productId
    form.productLabel = `${d.productCode} ${d.productName}`
    form.plannedQty = d.plannedQty
    form.remark = d.remark
    const s = toDate(d.plannedStartAt)
    const e = toDate(d.plannedEndAt)
    form.range = s && e ? [s, e] : []
    // 回显产品进候选，避免远程搜索里没有历史项
    productOptions.value = [{
      id: d.productId, code: d.productCode, name: d.productName, spec: null,
      categoryCode: '', categoryLabel: '', unitName: d.unitName,
      status: '0', isProduct: true,
    }]
  } finally {
    loading.value = false
  }
}

async function submit() {
  const ok = await formRef.value?.validate().then(() => true).catch(() => false)
  if (!ok) return
  if (!editing.value && !form.productId) { ElMessage.warning('请选择成品'); return }
  if (!form.range || form.range.length < 2) { ElMessage.warning('请选择计划起止时间'); return }
  const plannedStartAt = toIso(form.range[0] as Date)
  const plannedEndAt = toIso(form.range[1] as Date)
  if (plannedEndAt <= plannedStartAt) { ElMessage.warning('结束时间须晚于开始时间'); return }

  submitting.value = true
  try {
    if (editing.value) {
      const detail = await updateWorkOrder(String(route.params.id), {
        plannedQty: form.plannedQty,
        plannedStartAt,
        plannedEndAt,
        remark: form.remark,
      })
      ElMessage.success('已保存')
      router.push(`/workorder/detail/${detail.id}`)
    } else {
      const res = await createWorkOrder({
        productId: form.productId,
        plannedQty: form.plannedQty,
        plannedStartAt,
        plannedEndAt,
        remark: form.remark,
      })
      ElMessage.success(`工单已创建：${res.workOrderNo}`)
      router.push(`/workorder/detail/${res.id}`)
    }
  } catch (e) {
    if (!(e instanceof ApiError)) return
    // 400/1001：数量输入异常（field=plannedQty）→ 表单就地提示
    if (e.code === BIZ_CODE.INVALID_PARAM) {
      ElMessage.error(paramError(e.data, 'plannedQty'))
      return
    }
    if (e.code === WORK_ORDER_BIZ_CODE.WORK_ORDER_QUANTITY_INVALID) {
      await showQuantityInvalid(e.data)
      return
    }
    if (e.code === WORK_ORDER_BIZ_CODE.MISSING_PRODUCTION_DEFINITION) {
      if (await showMissingDefinition(e.data)) router.push('/basic/bom')
      return
    }
    if (e.code === WORK_ORDER_BIZ_CODE.STATE_CONFLICT) {
      // 409/4100：状态冲突，请求层已弹 message，这里补结构化原因
      const reason = (e.data as { reason?: { code: string; message: string } } | undefined)?.reason
      if (reason) await ElMessageBox.alert(reason.message, '操作未完成', { type: 'warning' })
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => { searchProduct(''); if (editing.value) loadDetail() })
</script>

<template>
  <el-card v-loading="loading">
    <template #header><span class="title">{{ editing ? '编辑工单' : '手工新建工单' }}</span></template>

    <el-alert
      v-if="editing"
      class="mb"
      type="info"
      :closable="false"
      show-icon
      title="仅可修改计划数量、排期与备注；产品与绑定的 BOM / 工艺路线版本固定"
    />

    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" class="form">
      <el-form-item label="成品">
        <el-select
          v-if="!editing"
          v-model="form.productId" filterable remote clearable
          :remote-method="searchProduct" :loading="productLoading"
          placeholder="输入编码/名称搜索（仅成品）"
        >
          <el-option v-for="p in productOptions" :key="p.id" :value="p.id" :label="`${p.code} ${p.name}`" />
        </el-select>
        <el-input v-else :model-value="form.productLabel" disabled />
      </el-form-item>

      <el-form-item label="计划数量" prop="plannedQty">
        <el-input v-model="form.plannedQty" placeholder="如 100.0000" class="qty" />
        <span class="hint">四位小数；子件需求按此数量自动计算</span>
      </el-form-item>

      <el-form-item label="计划起止">
        <el-date-picker
          v-model="form.range" type="datetimerange"
          range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间"
          format="YYYY-MM-DD HH:mm" :default-time="[new Date(2000, 1, 1, 8, 0, 0), new Date(2000, 1, 1, 17, 0, 0)]"
        />
      </el-form-item>

      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="200" show-word-limit />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="router.back()">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-card>
</template>

<style scoped>
.title { font-weight: 600; }
.mb { margin-bottom: 12px; }
.form { max-width: 640px; }
.qty { width: 220px; }
.hint { margin-left: 8px; font-size: 12px; color: var(--el-text-color-secondary); }
</style>
