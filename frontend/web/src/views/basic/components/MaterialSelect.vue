<script setup lang="ts">
// 物料远程搜索下拉：契约要求候选走 /materials/options（仅会话、远程分页），不可全量拉。
// · parent=true  用于 BOM 父件 / 路线产品候选 → isProduct=true
// · 子件候选不传 isProduct、不传 status（默认仅启用）
// 已选但已停用的物料不在候选里，由调用方用明细自带的 code/name 兜底显示（见 placeholder 逻辑）。
import { ref, watch } from 'vue'
import { materialOptions } from '@/api'
import type { MaterialOption } from '@/types'

const props = withDefaults(defineProps<{
  modelValue: string
  /** 父件/产品候选：只列可生产物料 */
  parent?: boolean
  placeholder?: string
  disabled?: boolean
}>(), { parent: false, placeholder: '搜索编码或名称', disabled: false })

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const options = ref<MaterialOption[]>([])
const loading = ref(false)
/** 已选项的展示文案（候选里没有时也能显示） */
const fallbackLabel = ref('')

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

watch(() => props.modelValue, (id) => {
  const hit = options.value.find((o) => o.id === id)
  if (hit) fallbackLabel.value = `${hit.code} ${hit.name}`
}, { immediate: true })

defineExpose({ setFallback: (label: string) => { fallbackLabel.value = label } })
</script>

<template>
  <el-select
    :model-value="modelValue"
    :placeholder="fallbackLabel || placeholder"
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
    <el-option v-for="o in options" :key="o.id" :label="`${o.code} ${o.name}`" :value="o.id">
      <span>{{ o.code }} {{ o.name }}</span>
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
