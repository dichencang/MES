<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listOperLogs, getOperLog, clearOperLogs } from '@/api'
import type { OperLog } from '@/types'
import { formatDateTime } from '@/utils/time'

const loading = ref(false)
const rows = ref<OperLog[]>([])
const total = ref(0)
const query = reactive({ operatorName: '', module: '', status: '', timeRange: [] as string[], page: 1, pageSize: 10 })

const detailVisible = ref(false)
const detail = ref<OperLog | null>(null)

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: query.page, pageSize: query.pageSize }
    if (query.operatorName) params.operatorName = query.operatorName
    if (query.module) params.module = query.module
    if (query.status) params.status = query.status
    if (query.timeRange?.length === 2) {
      params.startTime = query.timeRange[0]
      params.endTime = query.timeRange[1]
    }
    const res = await listOperLogs(params); rows.value = res.list; total.value = res.total
  } finally { loading.value = false }
}
async function openDetail(id: string) { detail.value = await getOperLog(id); detailVisible.value = true }
async function clearAll() {
  await ElMessageBox.confirm('确认清空全部操作日志？此操作不可撤销。', '警告', { type: 'warning', confirmButtonText: '确认清空' })
  await clearOperLogs(); ElMessage.success('已清空'); query.page = 1; load()
}
onMounted(load)
</script>

<template>
  <div class="page">
    <el-card>
      <template #header><div class="toolbar"><span class="title">操作日志</span>
        <el-button v-perm="'system:oper-log:clear'" type="danger" @click="clearAll">清空日志</el-button>
      </div></template>
      <el-form :inline="true" :model="query" class="search">
        <el-form-item label="操作人"><el-input v-model="query.operatorName" placeholder="操作人" clearable /></el-form-item>
        <el-form-item label="模块"><el-input v-model="query.module" placeholder="模块" clearable /></el-form-item>
        <el-form-item label="结果"><el-select v-model="query.status" placeholder="全部" clearable style="width: 100px"><el-option label="成功" value="0" /><el-option label="失败" value="1" /></el-select></el-form-item>
        <el-form-item label="时间">
          <el-date-picker v-model="query.timeRange" type="datetimerange" range-separator="至"
            start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DDTHH:mm:ssZ" />
        </el-form-item>
        <el-form-item><el-button type="primary" @click="query.page = 1; load()">查询</el-button><el-button @click="Object.assign(query, { operatorName: '', module: '', status: '', timeRange: [], page: 1 }); load()">重置</el-button></el-form-item>
      </el-form>
      <el-table :data="rows" v-loading="loading" border stripe>
        <el-table-column prop="operatorName" label="操作人" width="110" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="operation" label="操作描述" min-width="200" />
        <el-table-column prop="requestUrl" label="请求地址" min-width="200" />
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column label="结果" width="80">
          <template #default="{ row }"><el-tag size="small" :type="(row as OperLog).status === '0' ? 'success' : 'danger'">{{ (row as OperLog).status === '0' ? '成功' : '失败' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="costTime" label="耗时(ms)" width="100" />
        <el-table-column label="操作时间" width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDateTime((row as OperLog).operTime) }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="80">
          <template #default="{ row }">
            <el-button v-perm="'system:oper-log:query'" link type="primary" @click="openDetail((row as OperLog).id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="query.page" v-model:page-size="query.pageSize" :total="total"
        :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end" @current-change="load" @size-change="load" />
    </el-card>

    <el-dialog v-model="detailVisible" title="日志详情" width="640px">
      <el-descriptions :column="2" border v-if="detail">
        <el-descriptions-item label="操作人">{{ detail.operatorName }}</el-descriptions-item>
        <el-descriptions-item label="模块">{{ detail.module }}</el-descriptions-item>
        <el-descriptions-item label="操作描述" :span="2">{{ detail.operation }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ detail.method }}</el-descriptions-item>
        <el-descriptions-item label="请求地址">{{ detail.requestUrl }}</el-descriptions-item>
        <el-descriptions-item label="请求参数" :span="2"><pre class="code">{{ detail.requestParam }}</pre></el-descriptions-item>
        <el-descriptions-item label="IP">{{ detail.ip }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ detail.costTime }} ms</el-descriptions-item>
        <el-descriptions-item label="结果"><el-tag size="small" :type="detail.status === '0' ? 'success' : 'danger'">{{ detail.status === '0' ? '成功' : '失败' }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2">{{ detail.errorMsg || '—' }}</el-descriptions-item>
        <el-descriptions-item label="操作时间" :span="2">{{ formatDateTime(detail.operTime) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<style scoped>
.page, .toolbar { width: 100%; }
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.title { font-weight: 600; font-size: 16px; }
.search { margin-bottom: 8px; }
.code { margin: 0; white-space: pre-wrap; word-break: break-all; font-size: 12px; background: #f5f5f5; padding: 8px; border-radius: 4px; }
</style>
