<script setup lang="ts">
// 编辑排期（契约-计划管理 §3.6）。仅改 plannedQty / plannedStartAt / plannedEndAt / remark；来源订单行固定。
// 时间：datetime-local 输入（本地），提交转 UTC Z；回显从 UTC Z 转本地。
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getProductionPlan, updateProductionPlan } from '@/api'
import type { ProductionPlanDetail } from '@/types'
import { localInputToUtcZ, utcZToLocalInput } from '@/utils/time'

const route = useRoute()
const router = useRouter()
const id = String(route.params.id)
const loading = ref(true)
const submitting = ref(false)

const form = reactive({
  plannedQty: '',
  startLocal: '',
  endLocal: '',
  remark: null as string | null,
})

async function load() {
  loading.value = true
  try {
    const d: ProductionPlanDetail = await getProductionPlan(id)
    form.plannedQty = d.plannedQty
    form.startLocal = utcZToLocalInput(d.plannedStartAt)
    form.endLocal = utcZToLocalInput(d.plannedEndAt)
    form.remark = d.remark
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.plannedQty || Number(form.plannedQty) <= 0) { ElMessage.warning('计划数量须大于 0'); return }
  if (!form.startLocal || !form.endLocal) { ElMessage.warning('请选择起止时间'); return }
  if (new Date(form.endLocal) <= new Date(form.startLocal)) { ElMessage.warning('结束时间须晚于开始时间'); return }
  submitting.value = true
  try {
    await updateProductionPlan(id, {
      plannedQty: form.plannedQty,
      plannedStartAt: localInputToUtcZ(form.startLocal),
      plannedEndAt: localInputToUtcZ(form.endLocal),
      remark: form.remark,
    })
    ElMessage.success('已保存')
    router.push(`/plan/production-plan/view/${id}`)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <el-card v-loading="loading">
    <template #header><span class="title">编辑排期</span></template>
    <el-form label-width="100px">
      <el-form-item label="计划数量">
        <el-input v-model="form.plannedQty" placeholder="十进制，如 4.0000" />
      </el-form-item>
      <el-form-item label="开始时间">
        <el-date-picker v-model="form.startLocal" type="datetime" placeholder="选择开始时间" />
      </el-form-item>
      <el-form-item label="结束时间">
        <el-date-picker v-model="form.endLocal" type="datetime" placeholder="选择结束时间" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="3" />
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
</style>
