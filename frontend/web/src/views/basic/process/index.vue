<script setup lang="ts">
// 工序档案：与物料同构，差异仅字段。
// 契约要点（v1.2 §三）：code 创建后不可改；停用被生效路线引用 → 409+4003 + references。
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import PageTable from '@/components/common/PageTable.vue'
import { useCrud } from '@/composables/useCrud'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/request'
import { asReferences, createProcess, listProcesses, setProcessStatus, updateProcess } from '@/api'
import { PERM } from '@/constants/perm'
import { STATUS_ENABLED, STATUS_OPTIONS } from '@/constants'
import type { Process, ProcessCreatePayload, ProcessUpdatePayload, ReferenceItem } from '@/types'

const auth = useAuthStore()
const formRef = ref<FormInstance>()

const {
  loading, rows, total, query,
  dialogVisible, editing, submitting, form,
  load, search, resetQuery, openCreate, openEdit, submit,
} = useCrud<Process, Record<string, any>>({
  fetch: listProcesses,
  defaultQuery: () => ({ keyword: '', status: '' }),
  defaultForm: () => ({ code: '', name: '', description: '' }),
  create: (data) => createProcess(data as ProcessCreatePayload),
  update: (id, data) => updateProcess(id, data as unknown as ProcessUpdatePayload),
  // 编辑不含 code
  toPayload: (f, isEdit) => ({
    name: f.name,
    description: f.description || null,
    ...(isEdit ? {} : { code: f.code }),
  }),
  beforeSubmit: () => formRef.value?.validate().then(() => true).catch(() => false) ?? true,
})

const rules: FormRules = {
  code: [
    { required: true, message: '请输入工序编码', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_-]{1,50}$/, message: '编码只能含字母、数字、- 和 _，最长 50', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入工序名称', trigger: 'blur' }],
}

const dialogueTitle = computed(() => (editing.value ? '编辑工序' : '新建工序'))

async function toggleStatus(row: Process) {
  const next = row.status === STATUS_ENABLED ? '1' : '0'
  const action = next === '1' ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${action}工序「${row.code} ${row.name}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await setProcessStatus(row.id, next)
    ElMessage.success(`已${action}`)
    await load()
  } catch (e) {
    if (e instanceof ApiError && e.code === 4003) {
      const refs = asReferences(e.data)
      await ElMessageBox.alert(
        refs.length
          ? `该工序正被以下生效路线引用，请先调整后再${action}：\n\n${refs
              .map((r: ReferenceItem) => `· 工艺路线 ${r.productCode} ${r.productName}（${r.version}）`)
              .join('\n')}`
          : '该工序正被生效路线引用，请先调整后再操作。',
        `无法${action}`,
        { type: 'warning', confirmButtonText: '知道了' },
      )
    }
  }
}

onMounted(load)
</script>

<template>
  <PageTable
    title="工序档案"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #toolbar>
      <el-button v-if="auth.hasPerm(PERM.basic.process.create)" type="primary" @click="openCreate">
        新建工序
      </el-button>
    </template>

    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" placeholder="编码 / 名称" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable>
            <el-option v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column prop="code" label="编码" width="160" />
    <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
    <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
    <el-table-column label="状态" width="90">
      <template #default="{ row }">
        <el-tag size="small" :type="(row as Process).status === STATUS_ENABLED ? 'success' : 'info'">
          {{ (row as Process).status === STATUS_ENABLED ? '正常' : '停用' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="150" fixed="right">
      <template #default="{ row }">
        <el-button
          v-if="auth.hasPerm(PERM.basic.process.update)"
          link type="primary"
          @click="openEdit(row as Process)"
        >
          编辑
        </el-button>
        <el-button
          v-if="auth.hasPerm(PERM.basic.process.setStatus)"
          link
          :type="(row as Process).status === STATUS_ENABLED ? 'danger' : 'success'"
          @click="toggleStatus(row as Process)"
        >
          {{ (row as Process).status === STATUS_ENABLED ? '停用' : '启用' }}
        </el-button>
      </template>
    </el-table-column>
  </PageTable>

  <el-dialog v-model="dialogVisible" :title="dialogueTitle" width="520px" @closed="formRef?.resetFields()">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="工序编码" prop="code">
        <el-input v-model="form.code" :disabled="editing" placeholder="建后不可修改" maxlength="50" />
      </el-form-item>
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" maxlength="100" />
      </el-form-item>
      <el-form-item label="说明">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="200" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.search :deep(.el-input),
.search :deep(.el-select) {
  width: 160px;
}
</style>
