<script setup lang="ts">
// 工艺路线只读查看页：与 BOM 查看页同构，明细换为工序步骤（按 seq 升序）。
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getRouting } from '@/api'
import { formatDateTime } from '@/utils/time'
import { versionStatusText } from '../components/feedback'
import type { RoutingVersion } from '@/types'

const route = useRoute()
const router = useRouter()
const detail = ref<RoutingVersion | null>(null)
const loading = ref(true)

const id = computed(() => String(route.params.id ?? ''))
const steps = computed(() => [...(detail.value?.steps ?? [])].sort((a, b) => a.seq - b.seq))

async function load() {
  loading.value = true
  try {
    detail.value = await getRouting(id.value)
  } finally {
    loading.value = false
  }
}

watch(id, load)
onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <el-card>
      <template #header>
        <div class="head">
          <div class="head-left">
            <el-button link @click="router.push('/basic/routing')">← 返回列表</el-button>
            <span class="title">{{ detail?.productCode }} {{ detail?.productName }}</span>
            <el-tag v-if="detail" size="small" :type="detail.status === '1' ? 'success' : 'info'">
              {{ detail ? versionStatusText(detail.status) : '' }} {{ detail?.versionLabel }}
            </el-tag>
          </div>
          <el-button
            v-if="detail && detail.status === '0'"
            type="primary" plain
            @click="router.push(`/basic/routing/edit/${detail.id}`)"
          >
            编辑草稿
          </el-button>
        </div>
      </template>

      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="生效版本">
          {{ detail?.activeVersion ? `${detail.activeVersion.versionLabel}（${detail.activeVersion.publisherName}）` : '未配置' }}
        </el-descriptions-item>
        <el-descriptions-item label="最后保存人">{{ detail?.lastEditorName || '—' }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDateTime(detail?.updateTime) }}</el-descriptions-item>
      </el-descriptions>

      <el-table :data="steps" border size="small" class="lines">
        <el-table-column label="序号" width="90" prop="seq" />
        <el-table-column label="工序编码" width="150" prop="processCode" />
        <el-table-column label="工序名称" min-width="180" prop="processName" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.processStatus === '1'" size="small" type="danger">已停用</el-tag>
            <span v-else>正常</span>
          </template>
        </el-table-column>
        <el-table-column label="作业说明" min-width="240" prop="remark" show-overflow-tooltip />
        <template #empty>
          <el-empty description="暂无工序步骤" :image-size="60" />
        </template>
      </el-table>

      <div class="versions">
        <span class="lines-title">同产品版本</span>
        <el-tag
          v-for="v in detail?.versions ?? []"
          :key="v.id"
          :type="v.id === detail?.id ? 'primary' : v.status === '1' ? 'success' : 'info'"
          size="small"
          class="vtag"
          @click="router.push(`/basic/routing/view/${v.id}`)"
        >
          {{ v.versionLabel }} · {{ versionStatusText(v.status) }}
          <template v-if="v.publishedAt"> · {{ formatDateTime(v.publishedAt) }}</template>
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.title {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lines {
  margin-top: 16px;
}
.lines-title {
  font-weight: 600;
}
.versions {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.vtag {
  cursor: pointer;
}
</style>
