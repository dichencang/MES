<script setup lang="ts">
// 物料远程搜索下拉：契约要求候选走 /materials/options（仅会话、远程分页），不可全量拉。
// · parent=true  用于 BOM 父件 / 路线产品候选 → isProduct=true
// · 子件候选不传 isProduct、不传 status（默认仅启用）
// 关键：已选但**不在候选里**的物料（已停用 / 未加载）必须用明细自带的编码名称兜底，
// 否则 el-select 会直接显示原始 ID（曾出现明细列显示 "2" 的问题）。
import { computed, ref } from 'vue'
import { materialOptions } from '@/api'
import type { MaterialOption } from '@/types'

const props = withDefaults(defineProps<{
  modelValue: string
  /** 父件/产品候选：只列可生产物料 */
  parent?: boolean
  placeholder?: string
  disabled?: boolean
  /** 兜底展示文案（如 "M-002 螺丝 M8"），候选中找不到当前值时使用 */
  fallback?: string
}>(), { parent: false, placeholder: '搜索编码或名称', disabled: false, fallback: '' })

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const options = ref<MaterialOption[]>([])
const loading = ref(false)

/** 合并候选：当前值不在候选里时补一个伪选项，保证显示编码名称而不是 ID */
const merged = computed<MaterialOption[]>(() => {
  const id = props.modelValue
  if (!id) return options.value
  if (options.value.some((o) => o.id === id)) return options.value
  if (!props.fallback) return options.value
  return [
    {
      id, code: props.fallback, name: '', spec: null,
      categoryCode: '', categoryLabel: '', unitName: '', status: '1', isProduct: false,
    },
    ...options.value,
  ]
})

const labelOf = (o: MaterialOption) => `${o.code} ${o.name}`.trim()

async function search(keyword: string) {
  loading.value = true
  try {
    const res = await materialOptions({
      keyword: keyword || undefined,
      isProduct: props.parent ? true : undefined,
      page: 1,
      pageSize: 20,
    })
    options.value = res.list
  } finally {
    loading.value = false
  }
}

/** 打开时先拉一页默认候选（不搜索也有内容） */
function onVisible(visible: boolean) {
  if (visible && !options.value.length) void search('')
}
</script>

<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    filterable
    remote
    clearable
    :remote-method="search"
    :loading="loading"
    style="width: 100%"
    @visible-change="onVisible"
    @update:model-value="(v: string) => emit('update:modelValue', v)"
  >
    <el-option v-for="o in merged" :key="o.id" :label="labelOf(o)" :value="o.id">
      <span>{{ labelOf(o) }}</span>
      <span class="opt-meta">{{ o.spec || '' }} {{ o.unitName }}</span>
    </el-option>
  </el-select>
</template>

<style scoped>
.opt-meta {
  float: right;
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
