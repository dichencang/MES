<script setup lang="ts">
// 物料档案：列表 + 新建/编辑弹窗 + 启停用。
// 契约要点（v1.2 §二）：
//   · 列表返回全部可编辑字段，编辑直接用行数据填弹窗，不调详情接口
//   · code / unitCode 创建后不可改：编辑时置只读且不放进 payload
//   · 停用/取消可生产被生效配置引用 → 409+4003 + references，需列出引用方
//   · 字典走 material_category / material_unit（仅会话，已缓存）
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import PageTable from '@/components/common/PageTable.vue'
import { useCrud } from '@/composables/useCrud'
import { useDict } from '@/composables/useDict'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/request'
import {
  asReferences, createMaterial, listMaterials, setMaterialStatus, updateMaterial,
} from '@/api'
import { PERM } from '@/constants/perm'
import { BIZ_CODE } from '@/constants/biz'
import { STATUS_ENABLED, STATUS_OPTIONS } from '@/constants'
import type { Material, MaterialCreatePayload, MaterialUpdatePayload, ReferenceItem } from '@/types'

const auth = useAuthStore()
const { options: dictOptions } = useDict('material_category', 'material_unit')
const formRef = ref<FormInstance>()

const categoryOptions = computed(() => dictOptions('material_category'))
const unitOptions = computed(() => dictOptions('material_unit'))

const {
  loading, rows, total, query,
  dialogVisible, editing, editingId, submitting, form,
  load, search, resetQuery, openCreate, openEdit, submit,
} = useCrud<Material, Record<string, any>>({
  fetch: listMaterials,
  defaultQuery: () => ({ keyword: '', categoryCode: '', status: '', isProduct: '' }),
  defaultForm: () => ({
    code: '', name: '', categoryCode: '', spec: '', unitCode: '', isProduct: false, remark: '',
  }),
  create: (data) => createMaterial(data as MaterialCreatePayload),
  update: (id, data) => updateMaterial(id, data as unknown as MaterialUpdatePayload),
  // 编辑不含 code / unitCode（后端 extra="forbid"，携带会 400）
  toPayload: (f, isEdit) => ({
    name: f.name,
    categoryCode: f.categoryCode,
    spec: f.spec || null,
    isProduct: Boolean(f.isProduct),
    remark: f.remark || null,
    ...(isEdit ? {} : { code: f.code, unitCode: f.unitCode }),
  }),
  beforeSubmit: () => formRef.value?.validate().then(() => true).catch(() => false) ?? true,
})

const rules: FormRules = {
  code: [
    { required: true, message: '请输入物料编码', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_-]{1,50}$/, message: '编码只能含字母、数字、- 和 _，最长 50', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入物料名称', trigger: 'blur' }],
  categoryCode: [{ required: true, message: '请选择物料类别', trigger: 'change' }],
  unitCode: [{ required: true, message: '请选择基本单位', trigger: 'change' }],
}

const dialogueTitle = computed(() => (editing.value ? '编辑物料' : '新建物料'))

/** 启停用：4003 时列出被引用的生效配置 */
async function toggleStatus(row: Material) {
  const next = row.status === STATUS_ENABLED ? '1' : '0'
  const action = next === '1' ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${action}物料「${row.code} ${row.name}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await setMaterialStatus(row.id, next)
    ElMessage.success(`已${action}`)
    await load()
  } catch (e) {
    if (e instanceof ApiError && e.code === 4003) {
      const refs = asReferences(e.data)
      await ElMessageBox.alert(
        refs.length
          ? `该物料正被以下生效配置引用，请先调整后再${action}：\n\n${refs
              .map((r: ReferenceItem) => `· ${r.configType === 'BOM' ? 'BOM' : '工艺路线'} ${r.productCode} ${r.productName}（${r.version}）`)
              .join('\n')}`
          : '该物料正被生效配置引用，请先调整后再操作。',
        `无法${action}`,
        { type: 'warning', confirmButtonText: '知道了' },
      )
    }
    // 其余错误请求层已统一提示
  }
}

onMounted(load)
</script>

<template>
  <PageTable
    title="物料档案"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #toolbar>
      <el-button v-if="auth.hasPerm(PERM.basic.material.create)" type="primary" @click="openCreate">
        新建物料
      </el-button>
    </template>

    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" placeholder="编码 / 名称" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="query.categoryCode" placeholder="全部" clearable>
            <el-option v-for="o in categoryOptions" :key="o.dictValue" :label="o.dictLabel" :value="o.dictValue" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable>
            <el-option v-for="o in STATUS_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="可生产">
          <el-select v-model="query.isProduct" placeholder="全部" clearable>
            <el-option label="是" :value="true" />
            <el-option label="否" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column prop="code" label="编码" width="140" />
    <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
    <el-table-column prop="categoryLabel" label="类别" width="100" />
    <el-table-column prop="spec" label="规格" min-width="130" show-overflow-tooltip />
    <el-table-column prop="unitName" label="基本单位" width="90" />
    <el-table-column label="可生产" width="80">
      <template #default="{ row }">
        <el-tag v-if="(row as Material).isProduct" size="small" type="success">是</el-tag>
        <span v-else class="muted">否</span>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="80">
      <template #default="{ row }">
        <el-tag size="small" :type="(row as Material).status === STATUS_ENABLED ? 'success' : 'info'">
          {{ (row as Material).status === STATUS_ENABLED ? '正常' : '停用' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="170" fixed="right">
      <template #default="{ row }">
        <el-button
          v-if="auth.hasPerm(PERM.basic.material.update)"
          link type="primary"
          @click="openEdit(row as Material)"
        >
          编辑
        </el-button>
        <el-button
          v-if="auth.hasPerm(PERM.basic.material.setStatus)"
          link
          :type="(row as Material).status === STATUS_ENABLED ? 'danger' : 'success'"
          @click="toggleStatus(row as Material)"
        >
          {{ (row as Material).status === STATUS_ENABLED ? '停用' : '启用' }}
        </el-button>
      </template>
    </el-table-column>
  </PageTable>

  <el-dialog v-model="dialogVisible" :title="dialogueTitle" width="560px" @closed="formRef?.resetFields()">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
      <el-form-item label="物料编码" prop="code">
        <el-input v-model="form.code" :disabled="editing" placeholder="建后不可修改" maxlength="50" />
      </el-form-item>
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" maxlength="100" />
      </el-form-item>
      <el-form-item label="类别" prop="categoryCode">
        <el-select v-model="form.categoryCode" placeholder="请选择">
          <el-option v-for="o in categoryOptions" :key="o.dictValue" :label="o.dictLabel" :value="o.dictValue" />
        </el-select>
      </el-form-item>
      <el-form-item label="基本单位" prop="unitCode">
        <el-input
          v-if="editing"
          :model-value="(rows.find((r) => r.id === editingId)?.unitName) ?? ''"
          disabled
        />
        <el-select v-else v-model="form.unitCode" placeholder="建后不可修改">
          <el-option v-for="o in unitOptions" :key="o.dictValue" :label="o.dictLabel" :value="o.dictValue" />
        </el-select>
        <div v-if="editing" class="hint">基本单位创建后不可变更</div>
      </el-form-item>
      <el-form-item label="规格">
        <el-input v-model="form.spec" maxlength="100" />
      </el-form-item>
      <el-form-item label="可生产">
        <el-switch v-model="form.isProduct" />
        <span class="hint">可作 BOM 父件与工艺路线产品</span>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="200" show-word-limit />
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
.muted {
  color: var(--el-text-color-placeholder);
}
.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
