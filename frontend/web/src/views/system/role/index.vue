<script setup lang="ts">
import { reactive, ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  listRoles, saveRole, deleteRole, getRolePermissions, assignRolePermissions, setDataScope, getPermissionTree, getDeptTree,
} from '@/api'
import type { RoleItem, PermissionItem, DeptNode } from '@/types'

const loading = ref(false)
const rows = ref<RoleItem[]>([])
const total = ref(0)
const query = reactive({ roleName: '', roleCode: '', page: 1, pageSize: 10 })

const dialogVisible = ref(false)
const editing = ref<RoleItem | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ roleName: '', remark: '' })

const permDialog = ref(false)
const permTarget = ref<RoleItem | null>(null)
const permTreeRef = ref()
const permTree = ref<PermissionItem[]>([])
const permSaving = ref(false)

const scopeDialog = ref(false)
const scopeTarget = ref<RoleItem | null>(null)
const scopeValue = ref<RoleItem['dataScope']>('ALL')
const scopeDepts = ref<string[]>([])
const scopeTreeRef = ref()
const deptTree = ref<DeptNode[]>([])

function onScopeCheck() {
  scopeDepts.value = (scopeTreeRef.value?.getCheckedKeys() as string[] | undefined) ?? []
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: query.page, pageSize: query.pageSize }
    if (query.roleName) params.roleName = query.roleName
    if (query.roleCode) params.roleCode = query.roleCode
    const res = await listRoles(params)
    rows.value = res.list
    total.value = res.total
  } finally { loading.value = false }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { roleName: '', remark: '' })
  dialogVisible.value = true
}
function openEdit(row: RoleItem) {
  editing.value = row
  Object.assign(form, { roleName: row.roleName, remark: row.remark ?? '' })
  dialogVisible.value = true
}
async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const payload: Record<string, unknown> = { roleName: form.roleName, remark: form.remark || null }
  if (!editing.value) {
    payload.roleCode = createForm.roleCode
    payload.dataScope = createForm.dataScope
    payload.deptIds = createForm.deptIds
  }
  await saveRole(payload, editing.value?.id)
  ElMessage.success('已保存'); dialogVisible.value = false; load()
}
const createForm = reactive({ roleCode: '', dataScope: 'ALL' as RoleItem['dataScope'], deptIds: [] as string[] })

async function remove(row: RoleItem) {
  await ElMessageBox.confirm(`确认删除角色「${row.roleName}」？`, '提示', { type: 'warning' })
  await deleteRole(row.id); ElMessage.success('已删除'); load()
}

// 授权：三级均可勾选；半选态仅展示，保存只提交直接勾选的 id
async function openPerm(row: RoleItem) {
  permTarget.value = row
  if (!permTree.value.length) permTree.value = await getPermissionTree(false)
  const res = await getRolePermissions(row.id)
  permDialog.value = true
  await nextTick()
  // check-strictly：精确回显直接授权的节点，不自动带上父子
  permTreeRef.value?.setCheckedKeys(res.permissionIds, false)
}
async function submitPerm() {
  if (!permTarget.value) return
  permSaving.value = true
  try {
    // getCheckedKeys 只返回完全勾选节点，半选父节点不提交（契约 §四）
    const keys = permTreeRef.value?.getCheckedKeys() as string[] | undefined
    await assignRolePermissions(permTarget.value.id, keys ?? [])
    ElMessage.success('授权已保存'); permDialog.value = false; load()
  } finally { permSaving.value = false }
}

async function openScope(row: RoleItem) {
  scopeTarget.value = row
  scopeValue.value = row.dataScope
  scopeDepts.value = [...row.deptIds]
  if (!deptTree.value.length) deptTree.value = await getDeptTree(true)
  scopeDialog.value = true
  await nextTick()
  scopeTreeRef.value?.setCheckedKeys(row.deptIds, false)
}
async function submitScope() {
  if (!scopeTarget.value) return
  await setDataScope(scopeTarget.value.id, scopeValue.value, scopeValue.value === 'CUSTOM' ? scopeDepts.value : [])
  ElMessage.success('数据范围已保存'); scopeDialog.value = false; load()
}

const rules = { roleName: [{ required: true, message: '请输入角色名称', trigger: 'blur' }] }
const scopeOptions: Array<{ label: string; value: RoleItem['dataScope'] }> = [
  { label: '全部数据', value: 'ALL' }, { label: '自定义部门', value: 'CUSTOM' },
  { label: '本部门', value: 'DEPT' }, { label: '本部门及以下', value: 'DEPT_CHILD' }, { label: '仅本人', value: 'SELF' },
]

onMounted(load)
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="toolbar">
          <span class="title">角色管理</span>
          <el-button v-perm="'system:role:create'" type="primary" @click="openCreate">新增角色</el-button>
        </div>
      </template>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="角色名称"><el-input v-model="query.roleName" placeholder="角色名称" clearable /></el-form-item>
        <el-form-item label="角色编码"><el-input v-model="query.roleCode" placeholder="角色编码" clearable /></el-form-item>
        <el-form-item><el-button type="primary" @click="query.page = 1; load()">查询</el-button><el-button @click="Object.assign(query, { roleName: '', roleCode: '', page: 1 }); load()">重置</el-button></el-form-item>
      </el-form>

      <el-table :data="rows" v-loading="loading" border stripe>
        <el-table-column prop="roleName" label="角色名称" width="150" />
        <el-table-column prop="roleCode" label="角色编码" width="150" />
        <el-table-column label="数据范围" width="130">
          <template #default="{ row }">{{ scopeOptions.find(s => s.value === (row as RoleItem).dataScope)?.label }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" />
        <el-table-column label="操作" fixed="right" width="290">
          <template #default="{ row }">
            <template v-if="(row as RoleItem).isSuper === '0'">
              <el-button v-perm="'system:role:query'" link type="primary" @click="openPerm(row as RoleItem)">授权</el-button>
              <el-button v-perm="'system:role:set-data-scope'" link type="primary" @click="openScope(row as RoleItem)">数据范围</el-button>
              <el-button v-perm="'system:role:update'" link type="primary" @click="openEdit(row as RoleItem)">编辑</el-button>
              <el-button v-perm="'system:role:delete'" link type="danger" @click="remove(row as RoleItem)">删除</el-button>
            </template>
            <el-tag v-else size="small" type="warning">超级管理员</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" v-model:page-size="query.pageSize" :total="total"
        :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end" @current-change="load" @size-change="load" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑角色' : '新增角色'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <template v-if="!editing">
          <el-form-item label="角色编码" required><el-input v-model="createForm.roleCode" placeholder="创建后不可改" /></el-form-item>
          <el-form-item label="数据范围"><el-select v-model="createForm.dataScope" style="width: 100%"><el-option v-for="s in scopeOptions" :key="s.value" :label="s.label" :value="s.value" /></el-select></el-form-item>
        </template>
        <el-form-item label="角色名称" prop="roleName"><el-input v-model="form.roleName" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="submit">确定</el-button></template>
    </el-dialog>

    <!-- 授权弹窗：三级独立勾选，半选仅展示 -->
    <el-dialog v-model="permDialog" :title="`分配权限 · ${permTarget?.roleName}`" width="520px">
      <el-tree ref="permTreeRef" :data="permTree" show-checkbox node-key="id"
        :props="{ label: 'permName', children: 'children' }" default-expand-all
        :check-strictly="true" style="max-height: 420px; overflow: auto" />
      <template #footer>
        <el-button @click="permDialog = false">取消</el-button>
        <el-button v-perm="'system:role:assign-permissions'" type="primary" :loading="permSaving" @click="submitPerm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 数据范围 -->
    <el-dialog v-model="scopeDialog" :title="`数据范围 · ${scopeTarget?.roleName}`" width="480px">
      <el-form label-width="90px">
        <el-form-item label="范围类型"><el-select v-model="scopeValue" style="width: 100%"><el-option v-for="s in scopeOptions" :key="s.value" :label="s.label" :value="s.value" /></el-select></el-form-item>
        <el-form-item v-if="scopeValue === 'CUSTOM'" label="授权部门">
          <el-tree ref="scopeTreeRef" :data="deptTree" show-checkbox node-key="id"
            :props="{ label: 'deptName', children: 'children' }" default-expand-all
            check-strictly @check-change="onScopeCheck" style="max-height: 260px; overflow: auto" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="scopeDialog = false">取消</el-button><el-button type="primary" @click="submitScope">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page, .toolbar { width: 100%; }
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; font-size: 16px; }
.search { margin-bottom: 8px; }
</style>
