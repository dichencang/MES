<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPermissionTree, savePermission, deletePermission } from '@/api'
import type { PermissionItem } from '@/types'

const loading = ref(false)
const tree = ref<PermissionItem[]>([])
const dialogVisible = ref(false)
const editing = ref<PermissionItem | null>(null)
const form = reactive({
  parentId: '0', permName: '', permType: 'MENU' as PermissionItem['permType'],
  permissionCode: '', path: '', component: '', icon: '', orderNum: 0, visible: '0', status: '0',
})

async function load() {
  loading.value = true
  try { tree.value = await getPermissionTree(true) } finally { loading.value = false }
}
function openCreate(parent?: PermissionItem) {
  editing.value = null
  Object.assign(form, {
    parentId: parent?.id ?? '0', permName: '', permType: 'BUTTON',
    permissionCode: '', path: '', component: '', icon: '', orderNum: 0, visible: '0', status: '0',
  })
  dialogVisible.value = true
}
function openEdit(row: PermissionItem) {
  editing.value = row
  Object.assign(form, {
    parentId: row.parentId, permName: row.permName, permType: row.permType,
    permissionCode: row.permissionCode, path: row.path ?? '', component: row.component ?? '',
    icon: row.icon ?? '', orderNum: row.orderNum, visible: row.visible, status: row.status,
  })
  dialogVisible.value = true
}
async function submit() {
  const payload: Record<string, unknown> = {
    parentId: form.parentId, permName: form.permName, permType: form.permType,
    path: form.path || null, component: form.component || null, icon: form.icon || null,
    orderNum: form.orderNum, visible: form.visible, status: form.status,
  }
  if (!editing.value) payload.permissionCode = form.permissionCode
  await savePermission(payload, editing.value?.id)
  ElMessage.success('已保存'); dialogVisible.value = false; load()
}
async function remove(row: PermissionItem) {
  await ElMessageBox.confirm(`确认删除权限「${row.permName}」？被角色引用时无法删除。`, '提示', { type: 'warning' })
  await deletePermission(row.id); ElMessage.success('已删除'); load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="toolbar">
          <span class="title">权限管理</span>
          <el-button v-perm="'system:permission:create'" type="primary" @click="openCreate()">新增权限</el-button>
        </div>
      </template>
      <el-table :data="tree" v-loading="loading" row-key="id" border default-expand-all
        :tree-props="{ children: 'children' }">
        <el-table-column prop="permName" label="权限名称" min-width="200" />
        <el-table-column prop="permType" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="(row as PermissionItem).permType === 'DIR' ? 'warning' : (row as PermissionItem).permType === 'MENU' ? 'primary' : 'info'">
              {{ (row as PermissionItem).permType === 'DIR' ? '目录' : (row as PermissionItem).permType === 'MENU' ? '菜单' : '按钮' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="permissionCode" label="权限编码" min-width="200" />
        <el-table-column prop="path" label="路由" width="150" />
        <el-table-column prop="orderNum" label="排序" width="70" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }"><el-tag size="small" :type="(row as PermissionItem).status === '0' ? 'success' : 'info'">{{ (row as PermissionItem).status === '0' ? '正常' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="190">
          <template #default="{ row }">
            <el-button v-perm="'system:permission:create'" link type="primary" @click="openCreate(row as PermissionItem)">新增子级</el-button>
            <el-button v-perm="'system:permission:update'" link type="primary" @click="openEdit(row as PermissionItem)">编辑</el-button>
            <el-button v-perm="'system:permission:delete'" link type="danger" @click="remove(row as PermissionItem)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑权限' : '新增权限'" width="540px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="上级"><el-tree-select v-model="form.parentId" :data="tree" node-key="id"
          :props="{ label: 'permName', children: 'children' }" check-strictly style="width: 100%" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.permName" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.permType" style="width: 100%">
            <el-option label="目录" value="DIR" /><el-option label="菜单" value="MENU" /><el-option label="按钮" value="BUTTON" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限编码"><el-input v-model="form.permissionCode" :disabled="!!editing" placeholder="如 system:user:create" /></el-form-item>
        <template v-if="form.permType === 'MENU'">
          <el-form-item label="路由路径"><el-input v-model="form.path" placeholder="/system/user" /></el-form-item>
          <el-form-item label="组件路径"><el-input v-model="form.component" placeholder="system/user/index" /></el-form-item>
          <el-form-item label="图标"><el-input v-model="form.icon" placeholder="User" /></el-form-item>
        </template>
        <el-form-item label="排序"><el-input-number v-model="form.orderNum" /></el-form-item>
        <el-form-item label="可见"><el-select v-model="form.visible" style="width: 100%"><el-option label="显示" value="0" /><el-option label="隐藏" value="1" /></el-select></el-form-item>
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
