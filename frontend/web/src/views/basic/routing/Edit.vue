<script setup lang="ts">
// 工艺路线编辑页：与 BOM 编辑同构，差异：
//   · 明细是 steps，**seq 由用户填写**（正整数、本路线内唯一），不是后端生成
//   · 无 baseQty
//   · 提供「按 10 自动填充」便利按钮（纯前端重排，不改后端规则）
import { computed, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ApiError } from '@/api/request'
import { createRouting, deleteRouting, getRouting, processOptions, publishRouting, saveRouting } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { PERM } from '@/constants/perm'
import {
  confirmPublish, resolveActiveChanged, resolveDraftConflict, showPublishReasons, versionStatusText,
} from '../components/feedback'
import type { ProcessOption, RoutingVersion } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const id = String(route.params.id ?? '')

const loading = ref(true)
const saving = ref(false)
const publishing = ref(false)
const detail = ref<RoutingVersion | null>(null)
const draftToken = ref('')
const steps = ref<Array<RoutingVersion['steps'][number] & { _new?: boolean }>>([])
const dirty = ref(false)
/** 发布校验失败时要高亮的步骤行（4004 的 stepId，重复序号会给两条） */
const errorIds = ref<string[]>([])

const processChoices = ref<ProcessOption[]>([])
const seqPattern = /^\d{1,4}$/

const isDraft = computed(() => detail.value?.status === '0')
const canUpdate = computed(() => auth.hasPerm(PERM.basic.routing.update))
const canPublish = computed(() => auth.hasPerm(PERM.basic.routing.publish))
const canDelete = computed(() => auth.hasPerm(PERM.basic.routing.delete) && auth.hasPerm(PERM.basic.routing.query))
const editable = computed(() => isDraft.value && canUpdate.value)

async function load() {
  loading.value = true
  try {
    const res = await getRouting(id)
    detail.value = res
    draftToken.value = res.draftToken ?? ''
    steps.value = [...res.steps].sort((a, b) => a.seq - b.seq || a.stepId.localeCompare(b.stepId)).map((s) => ({ ...s }))
    dirty.value = false
  } finally {
    loading.value = false
  }
}

/** 合并候选：已选但不在候选里的工序（已停用/未加载）用明细自带名称兜底，避免显示 ID */
const processMerged = computed(() => {
  const known = new Set(processChoices.value.map((p) => p.id))
  const extras = steps.value
    .filter((s) => s.processId && !known.has(s.processId))
    .map((s) => ({
      id: s.processId, code: s.processCode, name: s.processName, status: s.processStatus,
    }))
  return [...extras, ...processChoices.value]
})

async function loadProcessChoices(keyword = '') {
  const res = await processOptions({ keyword: keyword || undefined, page: 1, pageSize: 50 })
  processChoices.value = res.list
}

function markDirty() {
  dirty.value = true
  errorIds.value = []
}

/** 发布校验失败的行标红；STEP_SEQ_DUPLICATE 会同时定位两条 */
function rowClass({ row }: { row: RoutingVersion['steps'][number] }) {
  return errorIds.value.includes(row.stepId) ? 'row-error' : ''
}

function addRow() {
  const maxSeq = steps.value.reduce((m, s) => Math.max(m, Number(s.seq) || 0), 0)
  steps.value.push({
    stepId: '', seq: maxSeq + 10, processId: '',
    processCode: '', processName: '', processStatus: '0', remark: '',
    _new: true,
  })
  markDirty()
}

function removeRow(index: number) {
  steps.value.splice(index, 1)
  markDirty()
}

/** 按 10 自动填充：把当前顺序重排为 10/20/30…（纯前端便利，仍为正整数、唯一、升序） */
function autoFillSeq() {
  steps.value = steps.value
    .slice()
    .sort((a, b) => Number(a.seq) - Number(b.seq))
    .map((s, i) => ({ ...s, seq: (i + 1) * 10 }))
  markDirty()
  ElMessage.success('已按 10 递增重排序号')
}

async function save(): Promise<RoutingVersion | null> {
  if (!detail.value) return null
  for (const [i, s] of steps.value.entries()) {
    if (!s.processId) {
      ElMessage.warning(`第 ${i + 1} 行未选择工序`)
      return null
    }
    if (!seqPattern.test(String(s.seq))) {
      ElMessage.warning(`第 ${i + 1} 行步骤序号需为 1–9999 的整数`)
      return null
    }
  }
  saving.value = true
  try {
    const saved = await saveRouting(id, {
      draftToken: draftToken.value,
      steps: steps.value.map((s) => ({
        ...(s.stepId ? { stepId: s.stepId } : {}),
        seq: Number(s.seq),
        processId: s.processId,
        remark: s.remark || null,
      })),
    })
    detail.value = saved
    draftToken.value = saved.draftToken ?? ''
    steps.value = [...saved.steps].sort((a, b) => a.seq - b.seq || a.stepId.localeCompare(b.stepId)).map((s) => ({ ...s }))
    dirty.value = false
    ElMessage.success('草稿已保存')
    return saved
  } catch (e) {
    await handleSaveError(e)
    return null
  } finally {
    saving.value = false
  }
}

async function handleSaveError(e: unknown) {
  if (!(e instanceof ApiError)) return
  if (e.code === 4001) {
    const data = (e.data ?? {}) as { lastEditorName?: string; lastUpdatedAt?: string }
    const choice = await resolveDraftConflict(data.lastEditorName ?? '', data.lastUpdatedAt ?? '')
    if (choice === 'reload') {
      await load()
      ElMessage.info('已加载最新草稿')
    } else if (choice === 'copy') {
      const copied = await saveAsCopy()
      if (copied) ElMessage.success(`已另存为草稿 ${copied.versionLabel}`)
    }
  } else if (e.code === 4005) {
    ElMessage.warning('该版本已不是草稿，无法保存')
    await load()
  }
}

async function saveAsCopy(): Promise<RoutingVersion | null> {
  if (!detail.value) return null
  const created = await createRouting({ productId: detail.value.productId, sourceVersionId: id })
  if (created.draftToken) {
    const saved = await saveRouting(created.id, {
      draftToken: created.draftToken,
      steps: steps.value.map((s) => ({
        seq: Number(s.seq),
        processId: s.processId,
        remark: s.remark || null,
      })),
    })
    dirty.value = false
    await router.replace(`/basic/routing/edit/${saved.id}`)
    return saved
  }
  await router.replace(`/basic/routing/edit/${created.id}`)
  return created
}

async function publish() {
  if (!detail.value) return
  if (dirty.value) {
    const ok = await ElMessageBox.confirm('有未保存的改动，发布前需先保存草稿。是否保存并继续？', '提示', {
      type: 'warning', confirmButtonText: '保存并继续', cancelButtonText: '取消',
    }).then(() => true).catch(() => false)
    if (!ok) return
    if (!(await save())) return
  }
  const d = detail.value
  if (!d) return
  const expected = d.activeVersion?.id ?? null
  if (!(await confirmPublish({ kind: '工艺路线', versionLabel: d.versionLabel, activeVersion: d.activeVersion }))) return

  publishing.value = true
  try {
    await publishRouting(id, { draftToken: draftToken.value, expectedActiveVersionId: expected })
    ElMessage.success(`${d.versionLabel} 已发布`)
    await load()
  } catch (e) {
    await handlePublishError(e)
  } finally {
    publishing.value = false
  }
}

async function handlePublishError(e: unknown) {
  if (!(e instanceof ApiError)) return
  if (e.code === 4001) {
    const data = (e.data ?? {}) as { lastEditorName?: string; lastUpdatedAt?: string }
    const choice = await resolveDraftConflict(data.lastEditorName ?? '', data.lastUpdatedAt ?? '')
    if (choice === 'reload') await load()
    else if (choice === 'copy') await saveAsCopy()
  } else if (e.code === 4002) {
    const data = (e.data ?? {}) as { activeVersion?: RoutingVersion['activeVersion'] }
    if (await resolveActiveChanged(data.activeVersion ?? null)) await load()
  } else if (e.code === 4004) {
    const { stepIds } = await showPublishReasons(e.data)
    errorIds.value = stepIds
    await load()
  } else if (e.code === 4005) {
    ElMessage.warning('该版本已不是草稿，无法发布')
    await load()
  }
}

async function removeDraft() {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm(
      `将删除草稿 ${detail.value.versionLabel}（共 ${steps.value.length} 条步骤），不可恢复。`,
      '删除草稿',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteRouting(id, draftToken.value)
    ElMessage.success('草稿已删除')
    dirty.value = false
    router.replace('/basic/routing')
  } catch (e) {
    if (e instanceof ApiError && e.code === 4001) {
      await ElMessageBox.alert('草稿已被他人修改，已重新加载，请确认后再删除。', '操作未完成', { type: 'warning' })
      await load()
    } else if (e instanceof ApiError && e.code === 4005) {
      ElMessage.warning('该版本已不是草稿，无法删除')
      await load()
    }
  }
}

const back = () => router.push('/basic/routing')

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('有未保存的改动，离开将丢失。是否继续离开？', '提示', {
      type: 'warning', confirmButtonText: '离开', cancelButtonText: '留下',
    })
    return true
  } catch {
    return false
  }
})

onMounted(async () => {
  await Promise.all([load(), loadProcessChoices()])
})
</script>

<template>
  <div v-loading="loading">
    <el-card>
      <template #header>
        <div class="head">
          <div class="head-left">
            <el-button link @click="back">← 返回列表</el-button>
            <span class="title">{{ detail?.productCode }} {{ detail?.productName }}</span>
            <el-tag
              v-if="detail" size="small"
              :type="detail.status === '0' ? 'warning' : detail.status === '1' ? 'success' : 'info'"
            >
              {{ detail ? versionStatusText(detail.status) : '' }} {{ detail?.versionLabel }}
            </el-tag>
          </div>
          <div class="head-right">
            <el-button @click="load">刷新</el-button>
            <el-button v-if="editable" type="primary" :loading="saving" @click="save">保存草稿</el-button>
            <el-button v-if="isDraft && canPublish" type="success" :loading="publishing" @click="publish">发布</el-button>
            <el-button v-if="isDraft && canDelete" type="danger" plain @click="removeDraft">删除草稿</el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="!isDraft"
        type="info" :closable="false" show-icon
        title="当前版本不可编辑"
        description="生效/历史版本只读。需要变更请从列表复制一份新草稿，或新建空白草稿。"
        class="notice"
      />

      <div class="lines-head">
        <span class="lines-title">工序步骤</span>
        <div v-if="editable">
          <el-button size="small" @click="autoFillSeq">按 10 自动填充</el-button>
          <el-button size="small" type="primary" plain @click="addRow">添加工序</el-button>
        </div>
      </div>

      <el-table :data="steps" border size="small" :fit="false" :row-class-name="rowClass">
        <el-table-column label="序号" width="90">
          <template #default="{ row }">
            <el-input v-model="row.seq" :disabled="!editable" @input="markDirty" />
          </template>
        </el-table-column>
        <el-table-column label="工序" width="280">
          <template #default="{ row }">
            <el-select
              v-if="editable"
              v-model="row.processId"
              filterable
              placeholder="选择工序"
              style="width: 100%"
              @change="(v: string) => { const hit = processMerged.find((p) => p.id === v); if (hit) { row.processCode = hit.code; row.processName = hit.name; row.processStatus = hit.status } markDirty() }"
            >
              <el-option v-for="p in processMerged" :key="p.id" :label="`${p.code} ${p.name}`.trim()" :value="p.id" />
            </el-select>
            <span v-else>{{ row.processCode }} {{ row.processName }}</span>
            <el-tag v-if="row.processStatus === '1'" size="small" type="danger" class="inline-tag">已停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="作业说明" width="260">
          <template #default="{ row }">
            <el-input v-model="row.remark" :disabled="!editable" maxlength="200" @input="markDirty" />
          </template>
        </el-table-column>
        <el-table-column v-if="editable" label="操作" width="70">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeRow($index)">移除</el-button>
          </template>
        </el-table-column>
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
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
:deep(.row-error > td.el-table__cell) {
  background: var(--el-color-danger-light-9) !important;
}
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
.head-right {
  flex-shrink: 0;
}
.title {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.notice {
  margin-bottom: 12px;
}
.lines-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 12px 0 8px;
}
.lines-title {
  font-weight: 600;
}
.inline-tag {
  margin-left: 6px;
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
