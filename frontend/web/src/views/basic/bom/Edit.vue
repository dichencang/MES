<script setup lang="ts">
// BOM 编辑页（独立全屏页，不带弹窗）。
// 契约 v1.2 §4.4 逐条语义 + §8.2~§8.5 交互：
//   · 整单保存 = 全量覆盖；明细**不带 sortNo**；行移动靠重排数组
//   · 草稿明细的 itemId 只传属于本草稿的；复制回放时清空 itemId
//   · 发布必须带 draftToken + expectedActiveVersionId（无生效版传 null）
//   · 4001/4002/4004/4005 分别处理
import { computed, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ApiError } from '@/api/request'
import { deleteBom, getBom, publishBom, saveBom } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { PERM } from '@/constants/perm'
import MaterialSelect from '../components/MaterialSelect.vue'
import {
  confirmPublish, resolveActiveChanged, resolveDraftConflict, showPublishReasons, versionStatusText,
} from '../components/feedback'
import type { BomItem, BomVersion, EnabledStatus } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const id = String(route.params.id ?? '')

const loading = ref(true)
const saving = ref(false)
const publishing = ref(false)
const detail = ref<BomVersion | null>(null)
/** 并发令牌：保存成功后必须替换为后端新下发的值 */
const draftToken = ref('')
const baseQty = ref('1.0000')
/** 明细编辑副本（按 sortNo 排序后渲染） */
const items = ref<Array<BomItem & { _new?: boolean }>>([])
const dirty = ref(false)
/** 发布校验失败时要高亮的明细行（4004 的 itemId） */
const errorIds = ref<string[]>([])

const isDraft = computed(() => detail.value?.status === '0')
const canUpdate = computed(() => auth.hasPerm(PERM.basic.bom.update))
const canPublish = computed(() => auth.hasPerm(PERM.basic.bom.publish))
const canDelete = computed(() => auth.hasPerm(PERM.basic.bom.delete) && auth.hasPerm(PERM.basic.bom.query))
const editable = computed(() => isDraft.value && canUpdate.value)

/** 数量合法性（允许暂存 ≤0，发布时才拦） */
const qtyPattern = /^-?\d{1,14}(\.\d{1,4})?$/

async function load() {
  loading.value = true
  try {
    const res = await getBom(id)
    detail.value = res
    // eslint-disable-next-line no-restricted-syntax -- 契约：token 原样保存，禁止任何字符串处理
    draftToken.value = res.draftToken ?? ''
    baseQty.value = res.baseQty
    items.value = [...res.items]
      .sort((a, b) => (a.sortNo ?? 0) - (b.sortNo ?? 0))
      .map((it) => ({ ...it }))
    dirty.value = false
  } finally {
    loading.value = false
  }
}

function markDirty() {
  dirty.value = true
  errorIds.value = []
}

/** 发布校验失败的行标红（契约 §7.2：按 itemId 定位） */
function rowClass({ row }: { row: BomItem }) {
  return errorIds.value.includes(row.itemId) ? 'row-error' : ''
}

function addRow() {
  items.value.push({
    itemId: '', materialId: '', materialCode: '', materialName: '',
    materialStatus: '0' as EnabledStatus, unitName: '', qty: '1.0000', _new: true,
  })
  markDirty()
}

function removeRow(index: number) {
  items.value.splice(index, 1)
  markDirty()
}

/** 上下移动 = 重排数组（后端按下标生成 sortNo，不能改序号值） */
function move(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= items.value.length) return
  const list = items.value
  const [row] = list.splice(index, 1)
  if (!row) return
  list.splice(target, 0, row)
  markDirty()
}

/** 保存（全量覆盖） */
async function save(): Promise<BomVersion | null> {
  if (!detail.value) return null
  for (const [i, row] of items.value.entries()) {
    if (!row.materialId) {
      ElMessage.warning(`第 ${i + 1} 行未选择子件`)
      return null
    }
    if (!qtyPattern.test(row.qty)) {
      ElMessage.warning(`第 ${i + 1} 行用量格式不正确（最多 4 位小数）`)
      return null
    }
  }
  if (!qtyPattern.test(baseQty.value)) {
    ElMessage.warning('基准产量格式不正确（最多 4 位小数）')
    return null
  }
  saving.value = true
  try {
    const saved = await saveBom(id, {
      draftToken: draftToken.value,
      baseQty: baseQty.value,
      // 绝不带 sortNo；itemId 只传属于本草稿的（新行为空则省略）
      items: items.value.map((r) => ({
        ...(r.itemId ? { itemId: r.itemId } : {}),
        materialId: r.materialId,
        qty: r.qty,
      })),
    })
    // 保存成功：整体刷新本地状态（token 已轮换、itemId 可能新增）
    detail.value = saved
    draftToken.value = saved.draftToken ?? ''
    baseQty.value = saved.baseQty
    items.value = [...saved.items].sort((a, b) => (a.sortNo ?? 0) - (b.sortNo ?? 0)).map((it) => ({ ...it }))
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
      // 复制为新草稿：以服务端内容为起点，本地改动带入新草稿；itemId 属于源版本，必须清空
      const copied = await saveAsCopy()
      if (copied) ElMessage.success(`已另存为草稿 ${copied.versionLabel}`)
    }
  } else if (e.code === 4005) {
    ElMessage.warning('该版本已不是草稿，无法保存')
    await load()
  }
}

/** 冲突时另存为新草稿：POST /boms {productId, sourceVersionId} 后跳转 */
async function saveAsCopy(): Promise<BomVersion | null> {
  if (!detail.value) return null
  const { createBom } = await import('@/api')
  const created = await createBom({ productId: detail.value.productId, sourceVersionId: id })
  // 把本地未保存改动写入新草稿（清空 itemId：它们属于源版本）
  const payload = items.value.map((r) => ({
    materialId: r.materialId,
    qty: r.qty,
  }))
  if (created.draftToken) {
    const saved = await saveBom(created.id, {
      draftToken: created.draftToken,
      baseQty: baseQty.value,
      items: payload,
    })
    dirty.value = false
    await router.replace(`/basic/bom/edit/${saved.id}`)
    return saved
  }
  await router.replace(`/basic/bom/edit/${created.id}`)
  return created
}

/** 发布：先保存把本地改动落库，再确认、再发布 */
async function publish() {
  if (!detail.value) return
  if (dirty.value) {
    const ok = await ElMessageBox.confirm('有未保存的改动，发布前需先保存草稿。是否保存并继续？', '提示', {
      type: 'warning', confirmButtonText: '保存并继续', cancelButtonText: '取消',
    }).then(() => true).catch(() => false)
    if (!ok) return
    const saved = await save()
    if (!saved) return
  }
  const d = detail.value
  if (!d) return
  const expected = d.activeVersion?.id ?? null
  if (!(await confirmPublish({ kind: 'BOM', versionLabel: d.versionLabel, activeVersion: d.activeVersion }))) return

  publishing.value = true
  try {
    await publishBom(id, { draftToken: draftToken.value, expectedActiveVersionId: expected })
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
    // token 失效优先于版本冲突（契约 §7.0）：先让用户处理草稿
    const data = (e.data ?? {}) as { lastEditorName?: string; lastUpdatedAt?: string }
    const choice = await resolveDraftConflict(data.lastEditorName ?? '', data.lastUpdatedAt ?? '')
    if (choice === 'reload') await load()
    else if (choice === 'copy') await saveAsCopy()
  } else if (e.code === 4002) {
    const data = (e.data ?? {}) as { activeVersion?: BomVersion['activeVersion'] }
    const again = await resolveActiveChanged(data.activeVersion ?? null)
    if (again) await load()
  } else if (e.code === 4004) {
    const { itemIds } = await showPublishReasons(e.data)
    errorIds.value = itemIds
    await load()
  } else if (e.code === 4005) {
    ElMessage.warning('该版本已不是草稿，无法发布')
    await load()
  }
}

/** 删除草稿：token 来自详情，4001 时重读并再次确认 */
async function removeDraft() {
  if (!detail.value) return
  const confirmText = `将删除草稿 ${detail.value.versionLabel}（共 ${items.value.length} 行明细），不可恢复。`
  try {
    await ElMessageBox.confirm(confirmText, '删除草稿', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch {
    return
  }
  try {
    await deleteBom(id, draftToken.value)
    ElMessage.success('草稿已删除')
    dirty.value = false
    router.replace('/basic/bom')
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

function back() {
  router.push('/basic/bom')
}

/** 未保存离开确认 */
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

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="editor">
    <el-card>
      <template #header>
        <div class="head">
          <div class="head-left">
            <el-button link @click="back">← 返回列表</el-button>
            <span class="title">
              {{ detail?.productCode }} {{ detail?.productName }}
            </span>
            <el-tag v-if="detail" size="small" :type="detail.status === '0' ? 'warning' : detail.status === '1' ? 'success' : 'info'">
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

      <el-form inline class="meta-form">
        <el-form-item label="基准产量">
          <el-input v-model="baseQty" :disabled="!editable" style="width: 140px" @input="markDirty" />
          <span class="hint">当前校验为大于 0 的整数</span>
        </el-form-item>
        <el-form-item label="最后保存人">
          <span>{{ detail?.lastEditorName || '—' }}</span>
        </el-form-item>
        <el-form-item label="更新时间">
          <span>{{ detail?.updateTime ? detail.updateTime.slice(0, 19).replace('T', ' ') : '—' }}</span>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!isDraft"
        type="info"
        :closable="false"
        show-icon
        title="当前版本不可编辑"
        description="生效/历史版本只读。需要变更请从列表复制一份新草稿，或新建空白草稿。"
        class="notice"
      />

      <div class="lines-head">
        <span class="lines-title">子件明细</span>
        <el-button v-if="editable" size="small" type="primary" plain @click="addRow">添加子件</el-button>
      </div>

      <el-table :data="items" border size="small" :row-class-name="rowClass">
        <el-table-column label="#" type="index" width="56" />
        <el-table-column label="子件" min-width="260">
          <template #default="{ row, $index }">
            <MaterialSelect
              v-if="editable"
              v-model="row.materialId"
              @update:model-value="(v: string) => { row.materialId = v; markDirty() }"
            />
            <span v-else>{{ row.materialCode }} {{ row.materialName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.materialStatus === '1'" size="small" type="danger">已停用</el-tag>
            <span v-else class="muted">正常</span>
          </template>
        </el-table-column>
        <el-table-column label="单位" width="80">
          <template #default="{ row }">{{ row.unitName || '—' }}</template>
        </el-table-column>
        <el-table-column label="用量" width="150">
          <template #default="{ row }">
            <el-input v-model="row.qty" :disabled="!editable" @input="markDirty" />
          </template>
        </el-table-column>
        <el-table-column v-if="editable" label="排序" width="120">
          <template #default="{ $index }">
            <el-button link :disabled="$index === 0" @click="move($index, -1)">上移</el-button>
            <el-button link :disabled="$index === items.length - 1" @click="move($index, 1)">下移</el-button>
          </template>
        </el-table-column>
        <el-table-column v-if="editable" label="操作" width="80">
          <template #default="{ $index }">
            <el-button link type="danger" @click="removeRow($index)">移除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无子件" :image-size="60" />
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
          @click="router.push(`/basic/bom/view/${v.id}`)"
        >
          {{ v.versionLabel }} · {{ versionStatusText(v.status) }}
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
:deep(.row-error) {
  background: var(--el-color-danger-light-9);
}
.editor {
  padding: 0;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.meta-form {
  margin-bottom: 8px;
}
.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
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
.muted {
  color: var(--el-text-color-placeholder);
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
