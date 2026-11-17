<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listConfigs, saveConfig, deleteConfig } from '@/api'
import type { ConfigItem } from '@/types'

const loading = ref(false)
const rows = ref<ConfigItem[]>([])
const query = reactive({ configName: '', configKey: '', page: 1, pageSize: 10 })
const total = ref(0)

const dialogVisible = ref(false)
const editing = ref(false)
const form = reactive({ configName: '', configKey: '', configValue: '', remark: '' })
const editingCell = ref<string | null>(null)
const cellValue = ref('')
const inputRef = ref()

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: query.page, pageSize: query.pageSize }
    if (query.configName) params.configName = query.configName
    if (query.configKey) params.configKey = query.configKey
    const res = await listConfigs(params); rows.value = res.list; total.value = res.total
  } finally { loading.value = false }
}
function openCreate() { editing.value = false; Object.assign(form, { configName: '', configKey: '', configValue: '', remark: '' }); dialogVisible.value = true }
async function submit() {
  const payload: Record<string, unknown> = { configName: form.configName, configValue: form.configValue, remark: form.remark || null }
  if (!editing.value) payload.configKey = form.configKey
  await saveConfig(payload, undefined)
  ElMessage.success('已创建'); dialogVisible.value = false; load()
}
async function remove(row: ConfigItem) {
  await ElMessageBox.confirm(`确认删除参数「${row.configName}」？内置参数不可删除。`, '提示', { type: 'warning' })
  await deleteConfig(row.id); ElMessage.success('已删除'); load()
}

async function startEdit(row: ConfigItem) {
  editingCell.value = row.id; cellValue.value = row.configValue
  await nextTick(); inputRef.value?.focus()
}
async function commitEdit(row: ConfigItem) {
  if (editingCell.value !== row.id) return
  editingCell.value = null
  if (cellValue.value !== row.configValue) {
    await saveConfig({ configValue: cellValue.value }, row.id)
    ElMessage.success('已更新'); load()
  }
}
onMounted(load)
</script>

<template>
  <div class="page">
    <el-card>
      <template #header><div class="toolbar"><span class="title">系统参数</span>
        <el-button v-perm="'system:config:create'" type="primary" @click="openCreate">新增参数</el-button>
      </div></template>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="参数名"><el-input v-model="query.configName" placeholder="参数名" clearable /></el-form-item>
        <el-form-item label="参数键"><el-input v-model="query.configKey" placeholder="参数键" clearable /></el-form-item>
        <el-form-item><el-button type="primary" @click="query.page = 1; load()">查询</el-button><el-button @click="Object.assign(query, { configName: '', configKey: '', page: 1 }); load()">重置</el-button></el-form-item>
      </el-form>
      <el-table :data="rows" v-loading="loading" border stripe>
        <el-table-column prop="configName" label="参数名" width="160" />
        <el-table-column prop="configKey" label="参数键" min-width="180" />
        <el-table-column label="参数值" min-width="220">
          <template #default="{ row }">
            <el-input v-if="editingCell === (row as ConfigItem).id" ref="inputRef" v-model="cellValue" size="small"
              @blur="commitEdit(row as ConfigItem)" @keyup.enter="commitEdit(row as ConfigItem)" />
            <span v-else @click="startEdit(row as ConfigItem)" class="editable">{{ (row as ConfigItem).configValue }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }"><el-tag size="small" :type="(row as ConfigItem).configType === '0' ? 'warning' : 'info'">{{ (row as ConfigItem).configType === '0' ? '内置' : '自定义' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="140" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button v-if="(row as ConfigItem).configType === '1'" v-perm="'system:config:delete'" link type="danger" @click="remove(row as ConfigItem)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" v-model:page-size="query.pageSize" :total="total"
        :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end" @current-change="load" @size-change="load" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增参数" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="参数名"><el-input v-model="form.configName" /></el-form-item>
        <el-form-item label="参数键"><el-input v-model="form.configKey" /></el-form-item>
        <el-form-item label="参数值"><el-input v-model="form.configValue" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="submit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page, .toolbar { width: 100%; }
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; font-size: 16px; }
.search { margin-bottom: 8px; }
.editable { cursor: pointer; padding: 4px 6px; border-radius: 3px; }
.editable:hover { background: #ecf5ff; }
</style>
