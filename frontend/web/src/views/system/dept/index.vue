<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDeptTree, saveDept, deleteDept } from '@/api'
import type { DeptNode } from '@/types'

const loading = ref(false)
const tree = ref<DeptNode[]>([])
const dialogVisible = ref(false)
const editing = ref<DeptNode | null>(null)
const form = reactive({ parentId: '0', deptName: '', orderNum: 0, leader: '', phone: '', status: '0' })

async function load() {
  loading.value = true
  try { tree.value = await getDeptTree(true) } finally { loading.value = false }
}
function openCreate(parent?: DeptNode) {
  editing.value = null
  Object.assign(form, { parentId: parent?.id ?? '0', deptName: '', orderNum: 0, leader: '', phone: '', status: '0' })
  dialogVisible.value = true
}
function openEdit(row: DeptNode) {
  editing.value = row
  Object.assign(form, { parentId: row.parentId, deptName: row.deptName, orderNum: row.orderNum, leader: row.leader ?? '', phone: row.phone ?? '', status: row.status })
  dialogVisible.value = true
}
async function submit() {
  const payload: Record<string, unknown> = {
    parentId: form.parentId, deptName: form.deptName, orderNum: form.orderNum,
    leader: form.leader || null, phone: form.phone || null, status: form.status,
  }
  await saveDept(payload, editing.value?.id)
  ElMessage.success('已保存'); dialogVisible.value = false; load()
}
async function remove(row: DeptNode) {
  await ElMessageBox.confirm(`确认删除部门「${row.deptName}」？存在子部门或归属用户时无法删除。`, '提示', { type: 'warning' })
  await deleteDept(row.id); ElMessage.success('已删除'); load()
}
onMounted(load)
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="toolbar"><span class="title">组织架构</span>
          <el-button v-perm="'system:dept:create'" type="primary" @click="openCreate()">新增部门</el-button>
        </div>
      </template>
      <el-table :data="tree" v-loading="loading" row-key="id" border default-expand-all :tree-props="{ children: 'children' }">
        <el-table-column prop="deptName" label="部门名称" min-width="220" />
        <el-table-column prop="leader" label="负责人" width="120" />
        <el-table-column prop="phone" label="联系电话" width="140" />
        <el-table-column prop="orderNum" label="排序" width="80" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><el-tag size="small" :type="(row as DeptNode).status === '0' ? 'success' : 'info'">{{ (row as DeptNode).status === '0' ? '正常' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button v-perm="'system:dept:create'" link type="primary" @click="openCreate(row as DeptNode)">新增子级</el-button>
            <el-button v-perm="'system:dept:update'" link type="primary" @click="openEdit(row as DeptNode)">编辑</el-button>
            <el-button v-perm="'system:dept:delete'" link type="danger" @click="remove(row as DeptNode)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑部门' : '新增部门'" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="上级部门">
          <el-tree-select v-model="form.parentId" :data="tree" node-key="id" :props="{ label: 'deptName', children: 'children' }" check-strictly style="width: 100%" />
        </el-form-item>
        <el-form-item label="部门名称"><el-input v-model="form.deptName" /></el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.leader" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.orderNum" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="form.status" style="width: 100%"><el-option label="正常" value="0" /><el-option label="停用" value="1" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="submit">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page, .toolbar { width: 100%; }
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; font-size: 16px; }
</style>
