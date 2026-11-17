<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listDictTypes, saveDictType, deleteDictType, listDictData, saveDictData, deleteDictData } from '@/api'
import type { DictType, DictDataItem } from '@/types'

const loading = ref(false)
const types = ref<DictType[]>([])
const dictItems = ref<DictDataItem[]>([])
const currentType = ref<DictType | null>(null)

const typeDialog = ref(false)
const editingType = ref<DictType | null>(null)
const typeForm = reactive({ dictName: '', dictCode: '', status: '0', remark: '' })

const itemDialog = ref(false)
const editingItem = ref<DictDataItem | null>(null)
const itemForm = reactive({ dictLabel: '', dictValue: '', orderNum: 0, status: '0' })

async function loadTypes() {
  const res = await listDictTypes({ page: 1, pageSize: 100 })
  types.value = res.list
  if (types.value.length && !currentType.value) await selectType(types.value[0]!)
}
async function selectType(row: DictType) {
  currentType.value = row
  itemsLoading.value = true
  try { const res = await listDictData(row.dictCode); dictItems.value = res.list } finally { itemsLoading.value = false }
}
const itemsLoading = ref(false)

function openTypeCreate() { editingType.value = null; Object.assign(typeForm, { dictName: '', dictCode: '', status: '0', remark: '' }); typeDialog.value = true }
function openTypeEdit(row: DictType) { editingType.value = row; Object.assign(typeForm, { dictName: row.dictName, dictCode: row.dictCode, status: row.status, remark: row.remark ?? '' }); typeDialog.value = true }
async function submitType() {
  const payload: Record<string, unknown> = { dictName: typeForm.dictName, status: typeForm.status, remark: typeForm.remark || null }
  if (!editingType.value) payload.dictCode = typeForm.dictCode
  await saveDictType(payload, editingType.value?.id)
  ElMessage.success('已保存'); typeDialog.value = false; loadTypes()
}
async function removeType(row: DictType) {
  await ElMessageBox.confirm(`确认删除字典类型「${row.dictName}」？有字典项时无法删除。`, '提示', { type: 'warning' })
  await deleteDictType(row.id); ElMessage.success('已删除'); currentType.value = null; loadTypes()
}

function openItemCreate() { editingItem.value = null; Object.assign(itemForm, { dictLabel: '', dictValue: '', orderNum: 0, status: '0' }); itemDialog.value = true }
function openItemEdit(row: DictDataItem) { editingItem.value = row; Object.assign(itemForm, { dictLabel: row.dictLabel, dictValue: row.dictValue, orderNum: row.orderNum, status: row.status }); itemDialog.value = true }
async function submitItem() {
  if (!currentType.value) return
  const payload: Record<string, unknown> = { dictCode: currentType.value.dictCode, dictLabel: itemForm.dictLabel, dictValue: itemForm.dictValue, orderNum: itemForm.orderNum, status: itemForm.status }
  await saveDictData(payload, editingItem.value?.id)
  ElMessage.success('已保存'); itemDialog.value = false; selectType(currentType.value)
}
async function removeItem(row: DictDataItem) {
  await ElMessageBox.confirm('确认删除该字典项？已被业务引用的项建议停用而非删除。', '提示', { type: 'warning' })
  await deleteDictData(row.id); ElMessage.success('已删除'); if (currentType.value) selectType(currentType.value)
}

onMounted(loadTypes)
</script>

<template>
  <div class="page">
    <el-card>
      <template #header><span class="title">数据字典</span></template>
      <el-row :gutter="16">
        <el-col :span="7">
          <div class="col-head">
            <span>字典类型</span>
            <el-button v-perm="'system:dict:type-create'" link type="primary" @click="openTypeCreate">新增</el-button>
          </div>
          <el-table :data="types" v-loading="loading" highlight-current-row border
            @current-change="(row: DictType) => row && selectType(row)">
            <el-table-column prop="dictName" label="名称" min-width="120" />
            <el-table-column prop="dictCode" label="编码" min-width="120" />
            <el-table-column label="操作" width="110">
              <template #default="{ row }">
                <el-button v-perm="'system:dict:type-update'" link type="primary" @click.stop="openTypeEdit(row as DictType)">编辑</el-button>
                <el-button v-perm="'system:dict:type-delete'" link type="danger" @click.stop="removeType(row as DictType)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
        <el-col :span="17">
          <div class="col-head">
            <span>字典项 · {{ currentType?.dictName || '—' }}</span>
            <el-button v-perm="'system:dict:item-create'" link type="primary" :disabled="!currentType" @click="openItemCreate">新增</el-button>
          </div>
          <el-table :data="dictItems" v-loading="itemsLoading" border>
            <el-table-column prop="dictLabel" label="显示文本" min-width="140" />
            <el-table-column prop="dictValue" label="实际值" min-width="120" />
            <el-table-column prop="orderNum" label="排序" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="(row as DictDataItem).status === '0' ? 'success' : 'info'">{{ (row as DictDataItem).status === '0' ? '正常' : '停用' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="130">
              <template #default="{ row }">
                <el-button v-perm="'system:dict:item-update'" link type="primary" @click="openItemEdit(row as DictDataItem)">编辑</el-button>
                <el-button v-perm="'system:dict:item-delete'" link type="danger" @click="removeItem(row as DictDataItem)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="typeDialog" :title="editingType ? '编辑字典类型' : '新增字典类型'" width="460px">
      <el-form :model="typeForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="typeForm.dictName" /></el-form-item>
        <el-form-item label="编码"><el-input v-model="typeForm.dictCode" :disabled="!!editingType" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="typeForm.status" style="width: 100%"><el-option label="正常" value="0" /><el-option label="停用" value="1" /></el-select></el-form-item>
        <el-form-item label="备注"><el-input v-model="typeForm.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="typeDialog = false">取消</el-button><el-button type="primary" @click="submitType">确定</el-button></template>
    </el-dialog>

    <el-dialog v-model="itemDialog" :title="editingItem ? '编辑字典项' : '新增字典项'" width="460px">
      <el-form :model="itemForm" label-width="80px">
        <el-form-item label="显示文本"><el-input v-model="itemForm.dictLabel" /></el-form-item>
        <el-form-item label="实际值"><el-input v-model="itemForm.dictValue" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="itemForm.orderNum" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="itemForm.status" style="width: 100%"><el-option label="正常" value="0" /><el-option label="停用" value="1" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="itemDialog = false">取消</el-button><el-button type="primary" @click="submitItem">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page, .col-head { width: 100%; }
.title { font-weight: 600; font-size: 16px; }
.col-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 600; }
</style>
