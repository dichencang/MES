<script setup lang="ts">
// 标准列表页骨架：标题栏 + 工具栏插槽 + 查询区插槽 + 表格（列由默认插槽提供）+ 分页。
// 页面用法：
//   <PageTable title="用户管理" :data="rows" :loading="loading" :total="total"
//     v-model:page="query.page" v-model:page-size="query.pageSize" @change="load">
//     <template #toolbar>…新增按钮…</template>
//     <template #search>…查询表单…</template>
//     <el-table-column … />
//   </PageTable>
import { PAGE_SIZES } from '@/constants'

withDefaults(defineProps<{
  title?: string
  data: readonly unknown[]
  loading?: boolean
  total: number
  page: number
  pageSize: number
}>(), { loading: false, title: '' })

const emit = defineEmits<{
  'update:page': [value: number]
  'update:pageSize': [value: number]
  /** 页码/每页条数变化，调用方在此重新拉数据 */
  change: []
}>()

function onPage(page: number) {
  emit('update:page', page)
  emit('change')
}

function onSize(size: number) {
  emit('update:pageSize', size)
  emit('update:page', 1)
  emit('change')
}
</script>

<template>
  <el-card class="page-table">
    <template #header>
      <div class="toolbar">
        <span class="title">{{ title }}</span>
        <div class="toolbar-actions"><slot name="toolbar" /></div>
      </div>
    </template>

    <slot name="search" />

    <el-table :data="data" v-loading="loading" border stripe>
      <slot />
      <template #empty>
        <el-empty description="暂无数据" :image-size="72" />
      </template>
    </el-table>

    <el-pagination
      v-if="total > 0"
      class="page-table__pager"
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      :page-sizes="[...PAGE_SIZES]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="onPage"
      @size-change="onSize"
    />
  </el-card>
</template>
