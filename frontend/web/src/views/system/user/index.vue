<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import {
  listUsers, saveUser, deleteUser, resetPassword, setUserStatus, assignUserRoles, allRoles, getDeptTree,
} from '@/api'
import type { UserItem, RoleItem, DeptNode } from '@/types'
import { formatDateTime } from '@/utils/time'

const loading = ref(false)
const rows = ref<UserItem[]>([])
const total = ref(0)
const query = reactive({ username: '', realName: '', deptId: '', status: '', page: 1, pageSize: 10 })
const roles = ref<RoleItem[]>([])
const depts = ref<DeptNode[]>([])

// 编辑弹窗：直接接收列表行数据，不发起详情请求（契约 §8.2）
const dialogVisible = ref(false)
const editing = ref<UserItem | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ realName: '', deptId: '', phone: '', email: '' })

const roleDialogVisible = ref(false)
const roleTarget = ref<UserItem | null>(null)
const checkedRoles = ref<string[]>([])

const pwDialogVisible = ref(false)
const pwTarget = ref<UserItem | null>(null)
const resetPw = ref('')

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: query.page, pageSize: query.pageSize }
    if (query.username) params.username = query.username
    if (query.realName) params.realName = query.realName
    if (query.deptId) params.deptId = query.deptId
    if (query.status) params.status = query.status
    const res = await listUsers(params)
    rows.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  const [rs, ds] = await Promise.all([allRoles(), getDeptTree(true)])
  roles.value = rs.list
  depts.value = ds
}

function openCreate() {
  editing.value = null
  Object.assign(form, { realName: '', deptId: '', phone: '', email: '' })
  dialogVisible.value = true
}

function openEdit(row: UserItem) {
  editing.value = row
  Object.assign(form, { realName: row.realName, deptId: row.deptId, phone: row.phone ?? '', email: row.email ?? '' })
  dialogVisible.value = true
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  // 新建时账号/密码/部门必填（后端 deptId 拒空串，前端先拦）
  if (!editing.value) {
    if (!createForm.username.trim()) { ElMessage.warning('请输入账号'); return }
    if (!createForm.password) { ElMessage.warning('请输入密码'); return }
    if (!form.deptId) { ElMessage.warning('请选择部门'); return }
  }
  const payload: Record<string, unknown> = {
    realName: form.realName, deptId: form.deptId,
    phone: form.phone || null, email: form.email || null,
  }
  if (!editing.value) {
    payload.username = createForm.username
    payload.password = createForm.password
    payload.roleIds = createForm.roleIds
    payload.status = '0'
  }
  await saveUser(payload, editing.value?.id)
  ElMessage.success(editing.value ? '已保存' : '已创建')
  dialogVisible.value = false
  load()
}

// 新建时额外字段（账号、密码、角色）
const createForm = reactive({ username: '', password: '', roleIds: [] as string[] })

function openRoles(row: UserItem) {
  roleTarget.value = row
  checkedRoles.value = row.roles.map((r) => r.id)
  roleDialogVisible.value = true
}
async function submitRoles() {
  if (!roleTarget.value) return
  await assignUserRoles(roleTarget.value.id, checkedRoles.value)
  ElMessage.success('角色已分配')
  roleDialogVisible.value = false
  load()
}

function openResetPw(row: UserItem) {
  pwTarget.value = row
  resetPw.value = ''
  pwDialogVisible.value = true
}
async function submitResetPw() {
  if (!pwTarget.value || !resetPw.value) return
  await resetPassword(pwTarget.value.id, resetPw.value)
  ElMessage.success('密码已重置')
  pwDialogVisible.value = false
}

async function toggleStatus(row: UserItem) {
  await setUserStatus(row.id, row.status === '0' ? '1' : '0')
  ElMessage.success('状态已更新')
  load()
}

async function remove(row: UserItem) {
  await ElMessageBox.confirm(`确认删除用户「${row.realName}」？`, '提示', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('已删除')
  load()
}

const rules = {
  realName: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  deptId: [{ required: true, message: '请选择部门', trigger: 'change' }],
}

onMounted(() => { load(); loadOptions() })
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="toolbar">
          <span class="title">用户管理</span>
          <el-button v-perm="'system:user:create'" type="primary" @click="openCreate">新增用户</el-button>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="账号"><el-input v-model="query.username" placeholder="账号" clearable /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="query.realName" placeholder="姓名" clearable /></el-form-item>
        <el-form-item label="部门">
          <el-select v-model="query.deptId" placeholder="全部" clearable style="width: 160px">
            <el-option v-for="d in depts" :key="d.id" :label="d.deptName" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="正常" value="0" /><el-option label="停用" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
          <el-button @click="Object.assign(query, { username: '', realName: '', deptId: '', status: '', page: 1 }); load()">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="rows" v-loading="loading" border stripe>
        <el-table-column prop="username" label="账号" width="130" />
        <el-table-column prop="realName" label="姓名" width="110" />
        <el-table-column prop="deptName" label="部门" width="120" />
        <el-table-column label="角色" min-width="150">
          <template #default="{ row }">{{ (row as UserItem).roles.map(r => r.roleName).join('、') || '—' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="(row as UserItem).status === '0' ? 'success' : 'info'">{{ (row as UserItem).status === '0' ? '正常' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDateTime((row as UserItem).createTime) }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="280">
          <template #default="{ row }">
            <template v-if="(row as UserItem).isBuiltin === '0'">
              <el-button v-perm="'system:user:update'" link type="primary" @click="openEdit(row as UserItem)">编辑</el-button>
              <el-button v-perm="'system:user:assign-roles'" link type="primary" @click="openRoles(row as UserItem)">角色</el-button>
              <el-button v-perm="'system:user:reset-password'" link type="primary" @click="openResetPw(row as UserItem)">重置密码</el-button>
              <el-button v-perm="'system:user:set-status'" link :type="(row as UserItem).status === '0' ? 'warning' : 'success'" @click="toggleStatus(row as UserItem)">{{ (row as UserItem).status === '0' ? '停用' : '启用' }}</el-button>
              <el-button v-perm="'system:user:delete'" link type="danger" @click="remove(row as UserItem)">删除</el-button>
            </template>
            <el-tag v-else size="small" type="warning">内置账号</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page" v-model:page-size="query.pageSize"
        :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end" @current-change="load" @size-change="load"
      />
    </el-card>

    <!-- 编辑 / 新建 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新增用户'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="76px">
        <template v-if="!editing">
          <el-form-item label="账号" required><el-input v-model="createForm.username" placeholder="登录账号（创建后不可改）" /></el-form-item>
          <el-form-item label="密码" required><el-input v-model="createForm.password" type="password" show-password /></el-form-item>
          <el-form-item label="角色"><el-select v-model="createForm.roleIds" multiple style="width: 100%"><el-option v-for="r in roles" :key="r.id" :label="r.roleName" :value="r.id" /></el-select></el-form-item>
        </template>
        <el-form-item label="姓名" prop="realName"><el-input v-model="form.realName" /></el-form-item>
        <el-form-item label="部门" prop="deptId">
          <el-select v-model="form.deptId" style="width: 100%"><el-option v-for="d in depts" :key="d.id" :label="d.deptName" :value="d.id" /></el-select>
        </el-form-item>
        <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 分配角色 -->
    <el-dialog v-model="roleDialogVisible" title="分配角色" width="420px">
      <div style="margin-bottom: 8px; color: #666">用户：{{ roleTarget?.realName }}</div>
      <el-checkbox-group v-model="checkedRoles">
        <el-checkbox v-for="r in roles" :key="r.id" :value="r.id" style="display: block">{{ r.roleName }}</el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRoles">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="pwDialogVisible" title="重置密码" width="420px">
      <div style="margin-bottom: 8px; color: #666">用户：{{ pwTarget?.realName }}</div>
      <el-input v-model="resetPw" type="password" show-password placeholder="输入新密码" />
      <template #footer>
        <el-button @click="pwDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitResetPw">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page, .toolbar { width: 100%; }
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; font-size: 16px; }
.search { margin-bottom: 8px; }
</style>
