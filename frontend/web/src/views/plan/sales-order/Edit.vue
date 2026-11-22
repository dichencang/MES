<script setup lang="ts">
// 销售订单新建/编辑（契约-计划管理 §2.2/§2.6）。主表 + 多行明细，全量提交。
//  · 行号正整数、订单内唯一、删除不重排；编辑以明细 id 识别既有行
//  · 产品下拉远程搜索（materialOptions isProduct=true），回显走行内快照字段
//  · 数量十进制字符串，前端只校验 >0，不做算术
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createSalesOrder, getSalesOrder, materialOptions, updateSalesOrder } from '@/api'
import { ApiError } from '@/api/request'
import type { MaterialOption, SalesOrderDetail, SalesOrderItemInput } from '@/types'

const route = useRoute()
const router = useRouter()
const editing = computed(() => Boolean(route.params.id))
const formRef = ref<FormInstance>()
const submitting = ref(false)

interface FormRow extends SalesOrderItemInput {
  // 回显展示字段（不提交）
  productCode?: string
  productName?: string
  unitName?: string
  scheduledQty?: string
}

const form = reactive({
  customerName: '',
  orderDate: '',
  remark: null as string | null,
  items: [] as FormRow[],
})

const rules: FormRules = {
  customerName: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
  orderDate: [{ required: true, message: '请选择订单日期', trigger: 'change' }],
}

const productLoading = ref(false)
const productOptions = ref<MaterialOption[]>([])

async function searchProduct(keyword: string) {
  productLoading.value = true
  try {
    const res = await materialOptions({ keyword, isProduct: true, pageSize: 20 })
    productOptions.value = res.list
  } finally {
    productLoading.value = false
  }
}

function onProductChange(row: FormRow, productId: string) {
  const p = productOptions.value.find((x) => x.id === productId)
  row.productCode = p?.code
  row.productName = p?.name
  row.unitName = p?.unitName
}

function addRow() {
  const nextLine = form.items.length
    ? Math.max(...form.items.map((r) => r.lineNo ?? 0)) + 1
    : 1
  form.items.push({ lineNo: nextLine, productId: '', orderQty: '', dueDate: '' })
}

function removeRow(index: number) {
  form.items.splice(index, 1)
  // 删除不重排：保留其余行原行号
}

async function loadDetail() {
  const id = String(route.params.id)
  const d: SalesOrderDetail = await getSalesOrder(id)
  form.customerName = d.customerName
  form.orderDate = d.orderDate
  form.remark = d.remark
  form.items = d.items.map((it) => ({
    id: it.id,
    lineNo: it.lineNo,
    productId: it.productId,
    productCode: it.productCode,
    productName: it.productName,
    unitName: it.unitName,
    orderQty: it.orderQty,
    dueDate: it.dueDate,
    scheduledQty: it.scheduledQty,
  }))
  // 回显产品加入候选，避免远程搜索里没有历史项
  productOptions.value = d.items.map((it) => ({
    id: it.productId, code: it.productCode, name: it.productName, spec: null,
    categoryCode: '', categoryLabel: '', unitName: it.unitName,
    status: it.productStatus, isProduct: true,
  }))
}

function validateRows(): boolean {
  if (!form.items.length) {
    ElMessage.warning('请至少录入一行明细')
    return false
  }
  const lines = new Set<number>()
  for (const r of form.items) {
    if (!r.productId) { ElMessage.warning('请选择产品'); return false }
    if (!r.orderQty || Number(r.orderQty) <= 0) { ElMessage.warning('数量须大于 0'); return false }
    if (!r.dueDate) { ElMessage.warning('请选择交期'); return false }
    if (lines.has(r.lineNo)) { ElMessage.warning(`行号 ${r.lineNo} 重复`); return false }
    lines.add(r.lineNo)
  }
  return true
}

async function submit() {
  const ok = await formRef.value?.validate().then(() => true).catch(() => false)
  if (!ok || !validateRows()) return
  submitting.value = true
  try {
    const payload = {
      customerName: form.customerName,
      orderDate: form.orderDate,
      remark: form.remark,
      items: form.items.map((r) => ({
        ...(editing.value && r.id ? { id: r.id } : {}),
        lineNo: r.lineNo,
        productId: r.productId,
        orderQty: String(r.orderQty),
        dueDate: r.dueDate,
      })),
    }
    if (editing.value) {
      await updateSalesOrder(String(route.params.id), payload)
      ElMessage.success('已保存')
      router.push(`/plan/sales-order/view/${route.params.id}`)
    } else {
      const res = await createSalesOrder(payload)
      ElMessage.success('订单已创建')
      router.push(`/plan/sales-order/view/${res.id}`)
    }
  } catch (e) {
    if (e instanceof ApiError) {
      // 业务错误请求层已统一弹 message；结构化冲突在本页不特别处理（订单写入无专用码）
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => { searchProduct(''); if (editing.value) loadDetail() })
</script>

<template>
  <el-card>
    <template #header><span class="title">{{ editing ? '编辑销售订单' : '新建销售订单' }}</span></template>

    <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="客户名称" prop="customerName">
            <el-input v-model="form.customerName" maxlength="100" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="订单日期" prop="orderDate">
            <el-date-picker v-model="form.orderDate" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="200" />
      </el-form-item>

      <el-divider content-position="left">订单明细</el-divider>
      <!-- 窄容器下必须能一屏填完：行号/产品(含单位)/数量/交期/已排/操作，共 6 列，列宽压缩到 720px 内 -->
      <el-table :data="form.items" border size="small" class="items-table">
        <el-table-column label="行号" width="60" align="center">
          <template #default="{ row }">{{ (row as FormRow).lineNo }}</template>
        </el-table-column>
        <el-table-column label="产品" min-width="180">
          <template #default="{ row }">
            <el-select
              v-model="(row as FormRow).productId"
              filterable remote :remote-method="searchProduct" :loading="productLoading"
              placeholder="编码/名称搜索" @change="(v: string) => onProductChange(row as FormRow, v)"
            >
              <el-option
                v-for="p in productOptions" :key="p.id" :value="p.id"
                :label="`${p.code} ${p.name}`"
              />
            </el-select>
            <span v-if="(row as FormRow).unitName" class="unit-hint">{{ (row as FormRow).unitName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="订单数量" width="130">
          <template #default="{ row }">
            <el-input v-model="(row as FormRow).orderQty" placeholder="如 12.0000" />
          </template>
        </el-table-column>
        <el-table-column label="交期" width="140">
          <template #default="{ row }">
            <el-date-picker
              v-model="(row as FormRow).dueDate" type="date" value-format="YYYY-MM-DD"
              placeholder="交期" style="width: 100%"
            />
          </template>
        </el-table-column>
        <el-table-column label="已排" width="100">
          <template #default="{ row }">{{ (row as FormRow).scheduledQty ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeRow($index as number)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-button class="add-row" @click="addRow">+ 添加明细行</el-button>
    </el-form>

    <template #footer>
      <el-button @click="router.back()">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-card>
</template>

<style scoped>
.title { font-weight: 600; }
.add-row { margin-top: 12px; }
/* 明细列较多，窄屏兜底允许横向滚动，避免关键列（数量/交期）被挤到视口外 */
.items-table { width: 100%; }
.unit-hint {
  margin-left: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.items-table :deep(.el-date-editor) { width: 100%; }
</style>
