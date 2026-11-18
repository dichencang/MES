<script setup lang="ts">
// 用户管理：标准列表页 + 两个独立弹窗（分配角色、重置密码）。
// 契约要点：编辑不传 username/password/roleIds（改角色走 PUT /users/{id}/roles，防绕权）。
import { onMounted, ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import PageTable from '@/components/common/PageTable.vue'
import { useCrud } from '@/composables/useCrud'
import {
  listUsers, saveUser, deleteUser, resetPassword, setUserStatus, assignUserRoles, allRoles, getDeptTree,
} from '@/api'
import { PERM } from '@/constants/perm'
import { STATUS_OPTIONS } from '@/constants'
import { formatDateTime } from '@/utils/time'
import type { UserItem, RoleItem, DeptNode } from '@/types'

const roles = ref<RoleItem[]>([])
const depts = ref<DeptNode[]>([])
const formRef = ref<FormInstance>()

const rules = {
  realName: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  deptId: [{ required: true, message: '请选择部门', trigger: 'change' }],
}

const {
  loading, rows, total, query,
  dialogVisible, editing, submitting, form,
  load, search, resetQuery, openCreate, openEdit, submit, remove,
} = useCrud<UserItem>({
  fetch: listUsers,
  defaultQuery: () => ({ username: '', realName: '', deptId: '', status: '' }),
  defaultForm: () => ({
    username: '', password: '', roleIds: [] as string[],
    realName: '', deptId: '', phone: '', email: '',
  }),
  // 编辑弹窗直接用行数据回填（契约不设详情接口），这里只取可编辑字段
  toForm: (row) => ({
    realName: row.realName,
    deptId: row.deptId,
    phone: row.phone ?? '',
    email: row.email ?? '',
  }),
  create: (data) => saveUser(data),
  update: (id, data) => saveUser(data, id),
  remove: deleteUser,
  describe: (row) => row.realName,
  successText: { create: '已创建', update: '已保存' },
  beforeSubmit: async (f, isEdit) => {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return false
    // 新建时账号/密码/部门必填（后端拒空 deptId，前端先拦）
    if (!isEdit) {
      if (!String(f.username).trim()) { ElMessage.warning('请输入账号'); return false }
      if (!f.password) { ElMessage.warning('请输入密码'); return false }
      if (!f.deptId) { ElMessage.warning('请选择部门'); return false }
    }
    return true
  },
  // 编辑只提基本资料：username/password/roleIds 一律不带（角色走专用接口）
  toPayload: (f, isEdit) => {
    const base = {
      realName: f.realName,
      deptId: f.deptId,
      phone: f.phone || null,
      email: f.email || null,
    }
    return isEdit
      ? base
      : { ...base, username: f.username, password: f.password, roleIds: f.roleIds, status: '0' }
  },
})

async function loadOptions() {
  const [rs, ds] = await Promise.all([allRoles(), getDeptTree(true)])
  roles.value = rs.list
  depts.value = ds
}

async function toggleStatus(row: UserItem) {
  await setUserStatus(row.id, row.status === '0' ? '1' : '0')
  ElMessage.success('状态已更新')
  load()
}

// 分配角色（独立接口，防绕权）
const roleDialogVisible = ref(false)
const roleTarget = ref<UserItem | null>(null)
const checkedRoles = ref<string[]>([])

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

// 重置密码（契约：必须显式传新密码，空请求后端返回 400）
const pwDialogVisible = ref(false)
const pwTarget = ref<UserItem | null>(null)
const newPassword = ref('')

function openResetPw(row: UserItem) {
  pwTarget.value = row
  newPassword.value = ''
  pwDialogVisible.value = true
}

async function submitResetPw() {
  if (!pwTarget.value) return
  if (!newPassword.value) { ElMessage.warning('请输入新密码'); return }
  await resetPassword(pwTarget.value.id, newPassword.value)
  ElMessage.success('密码已重置')
  pwDialogVisible.value = false
}

onMounted(() => { load(); loadOptions() })
</script>

<template>
  <PageTable
    title="用户管理"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #toolbar>
      <el-button v-perm="PERM.user.create" type="primary" @click="openCreate">新增用户</el-button>
    </template>

    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="账号">
          <el-input v-model="query.username" placeholder="账号" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="query.realName" placeholder="姓名" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="query.deptId" placeholder="全部" clearable>
            <el-option v-for="d in depts" :key="d.id" :label="d.deptName" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable>
            <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column prop="username" label="账号" width="130" />
    <el-table-column prop="realName" label="姓名" width="110" />
    <el-table-column prop="deptName" label="部门" width="120" show-overflow-tooltip />
    <el-table-column label="角色" min-width="150">
      <template #default="{ row }">
        {{ (row as UserItem).roles.map((r) => r.roleName).join('、') || '—' }}
      </template>
    </el-table-column>
    <el-table-column prop="phone" label="手机号" width="130" />
    <el-table-column label="状态" width="80">
      <template #default="{ row }">
        <el-tag :type="(row as UserItem).status === '0' ? 'success' : 'info'">
          {{ (row as UserItem).status === '0' ? '正常' : '停用' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="创建时间" width="160" show-overflow-tooltip>
      <template #default="{ row }">{{ formatDateTime((row as UserItem).createTime) }}</template>
    </el-table-column>
    <el-table-column label="操作" fixed="right" width="300">
      <template #default="{ row }">
        <template v-if="(row as UserItem).isBuiltin === '0'">
          <el-button v-perm="PERM.user.update" link type="primary" @click="openEdit(row as UserItem)">编辑</el-button>
          <el-button v-perm="PERM.user.assignRoles" link type="primary" @click="openRoles(row as UserItem)">角色</el-button>
          <el-button v-perm="PERM.user.resetPassword" link type="primary" @click="openResetPw(row as UserItem)">重置密码</el-button>
          <el-button
            v-perm="PERM.user.setStatus"
            link
            :type="(row as UserItem).status === '0' ? 'warning' : 'success'"
            @click="toggleStatus(row as UserItem)"
          >
            {{ (row as UserItem).status === '0' ? '停用' : '启用' }}
          </el-button>
          <el-button v-perm="PERM.user.delete" link type="danger" @click="remove(row as UserItem)">删除</el-button>
        </template>
        <el-tag v-else size="small" type="warning">内置账号</el-tag>
      </template>
    </el-table-column>
  </PageTable>

  <!-- 新增 / 编辑 -->
  <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新增用户'" width="520px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="76px">
      <template v-if="!editing">
        <el-form-item label="账号" required>
          <el-input v-model="form.username" placeholder="登录账号（创建后不可改）" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.roleIds" multiple style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.roleName" :value="r.id" />
          </el-select>
        </el-form-item>
      </template>
      <el-form-item label="姓名" prop="realName"><el-input v-model="form.realName" /></el-form-item>
      <el-form-item label="部门" prop="deptId">
        <el-select v-model="form.deptId" style="width: 100%">
          <el-option v-for="d in depts" :key="d.id" :label="d.deptName" :value="d.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item>
      <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>

  <!-- 分配角色 -->
  <el-dialog v-model="roleDialogVisible" title="分配角色" width="420px">
    <div class="dialog-tip">用户：{{ roleTarget?.realName }}</div>
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
    <div class="dialog-tip">用户：{{ pwTarget?.realName }}</div>
    <el-input v-model="newPassword" type="password" show-password placeholder="输入新密码" />
    <template #footer>
      <el-button @click="pwDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitResetPw">确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-tip {
  margin-bottom: 8px;
  color: #666;
}
</style>
