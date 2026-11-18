<script setup lang="ts">
// 样板页：标准列表页写法。新增业务页面照此结构复制即可。
// 结构 = PageTable（标题/工具栏/查询区/表格/分页）+ useCrud（查询/表单/增改删）+ PERM 常量。
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageTable from '@/components/common/PageTable.vue'
import { useCrud } from '@/composables/useCrud'
import { useAuthStore } from '@/stores/auth'
import { listConfigs, saveConfig, deleteConfig } from '@/api'
import { PERM } from '@/constants/perm'
import { CONFIG_CUSTOM } from '@/constants'
import type { ConfigItem } from '@/types'

const auth = useAuthStore()
const canUpdate = computed(() => auth.hasPerm(PERM.config.update))

const {
  loading, rows, total, query,
  dialogVisible, editing, submitting, form,
  load, search, resetQuery, openCreate, submit, remove,
} = useCrud<ConfigItem>({
  fetch: listConfigs,
  defaultQuery: () => ({ configName: '', configKey: '' }),
  defaultForm: () => ({ configName: '', configKey: '', configValue: '', remark: '' }),
  create: (data) => saveConfig(data),
  update: (id, data) => saveConfig(data, id),
  remove: deleteConfig,
  // 新增带 configKey，编辑只提交可变字段（参数键建后不可改）
  toPayload: (f, isEdit) => ({
    configName: f.configName,
    configValue: f.configValue,
    remark: f.remark || null,
    ...(isEdit ? {} : { configKey: f.configKey }),
  }),
  describe: (row) => row.configName,
})

// 参数值行内编辑（需 system:config:update）
const editingCell = ref<string | null>(null)
const cellValue = ref('')
const inputRef = ref<{ focus: () => void }>()

async function startEdit(row: ConfigItem) {
  if (!canUpdate.value) return
  editingCell.value = row.id
  cellValue.value = row.configValue
  await nextTick()
  inputRef.value?.focus()
}

async function commitEdit(row: ConfigItem) {
  if (editingCell.value !== row.id) return
  editingCell.value = null
  if (cellValue.value === row.configValue) return
  await saveConfig({ configValue: cellValue.value }, row.id)
  ElMessage.success('已更新')
  load()
}

onMounted(load)
</script>

<template>
  <PageTable
    title="系统参数"
    :data="rows"
    :loading="loading"
    :total="total"
    v-model:page="query.page"
    v-model:page-size="query.pageSize"
    @change="load"
  >
    <template #toolbar>
      <el-button v-perm="PERM.config.create" type="primary" @click="openCreate">新增参数</el-button>
    </template>

    <template #search>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="参数名">
          <el-input v-model="query.configName" placeholder="参数名" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="参数键">
          <el-input v-model="query.configKey" placeholder="参数键" clearable @keyup.enter="search" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </template>

    <el-table-column prop="configName" label="参数名" width="180" />
    <el-table-column prop="configKey" label="参数键" min-width="200" />
    <el-table-column label="参数值" min-width="240">
      <template #default="{ row }">
        <el-input
          v-if="editingCell === (row as ConfigItem).id"
          ref="inputRef"
          v-model="cellValue"
          size="small"
          @blur="commitEdit(row as ConfigItem)"
          @keyup.enter="commitEdit(row as ConfigItem)"
        />
        <span v-else-if="canUpdate" class="editable" @click="startEdit(row as ConfigItem)">
          {{ (row as ConfigItem).configValue }}
        </span>
        <span v-else>{{ (row as ConfigItem).configValue }}</span>
      </template>
    </el-table-column>
    <el-table-column label="类型" width="90">
      <template #default="{ row }">
        <el-tag size="small" :type="(row as ConfigItem).configType === '0' ? 'warning' : 'info'">
          {{ (row as ConfigItem).configType === '0' ? '内置' : '自定义' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
    <el-table-column label="操作" width="90" fixed="right">
      <template #default="{ row }">
        <el-button
          v-if="(row as ConfigItem).configType === CONFIG_CUSTOM"
          v-perm="PERM.config.delete"
          link
          type="danger"
          @click="remove(row as ConfigItem)"
        >
          删除
        </el-button>
      </template>
    </el-table-column>
  </PageTable>

  <el-dialog v-model="dialogVisible" :title="editing ? '编辑参数' : '新增参数'" width="480px">
    <el-form :model="form" label-width="80px">
      <el-form-item label="参数名"><el-input v-model="form.configName" /></el-form-item>
      <el-form-item label="参数键"><el-input v-model="form.configKey" :disabled="editing" placeholder="建后不可修改" /></el-form-item>
      <el-form-item label="参数值"><el-input v-model="form.configValue" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>
