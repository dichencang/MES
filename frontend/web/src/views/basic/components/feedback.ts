// 版本编辑的共用反馈：并发冲突、发布确认、发布校验定位、引用清单。
// 契约 v1.2 §8.2~§8.5 与 §7.2 的 UI 落点。BOM 与路线共用。
import { ElMessageBox } from 'element-plus'
import { asReferences, asReasons } from '@/api'
import type { ActiveVersion, PublishReason, ReferenceItem, VersionBrief } from '@/types'

export interface PublishContext {
  /** 'BOM' | '工艺路线'，仅用于文案 */
  kind: string
  /** 本版本号，如 V4 */
  versionLabel: string
  /** 当前生效版本（用户确认时看到的那个） */
  activeVersion: ActiveVersion | null
}

/** 发布前二次确认：契约要求明确"将替换当前生效版本" */
export async function confirmPublish(ctx: PublishContext): Promise<boolean> {
  const { kind, versionLabel, activeVersion } = ctx
  const text = activeVersion
    ? `将发布 ${kind} ${versionLabel}，替换当前生效版本 ${activeVersion.versionLabel}。\n\n替换后新工单按 ${versionLabel} 算料，已下发工单保留原用量。`
    : `这是该产品首个生效${kind}（${versionLabel}）。`
  try {
    await ElMessageBox.confirm(text, `确认发布 ${versionLabel}`, {
      type: 'warning',
      confirmButtonText: '确认发布',
      cancelButtonText: '取消',
    })
    return true
  } catch {
    return false
  }
}

/** 4001 草稿并发冲突：只给两个出口，不提供强制覆盖 */
export async function resolveDraftConflict(
  lastEditorName: string,
  lastUpdatedAt: string,
): Promise<'reload' | 'copy' | null> {
  try {
    const action = await ElMessageBox.confirm(
      `草稿已被「${lastEditorName || '他人'}」于 ${lastUpdatedAt || '刚刚'} 修改。\n\n` +
        '· 重新加载：丢弃你本次未保存的改动\n' +
        '· 复制为新草稿：保留你的改动，另存为一个新版本',
      '草稿已被修改',
      {
        type: 'warning',
        distinguishCancelAndClose: true,
        confirmButtonText: '重新加载',
        cancelButtonText: '复制为新草稿',
      },
    )
    return action === 'confirm' ? 'reload' : 'copy'
  } catch (e) {
    // 点取消 = 选择复制；点关闭 = 什么都不做
    return e === 'cancel' ? 'copy' : null
  }
}

/** 4002 发布时生效版本已变：需要重新读取并让用户确认 */
export async function resolveActiveChanged(activeVersion: ActiveVersion | null): Promise<boolean> {
  const text = activeVersion
    ? `生效版本已变为 ${activeVersion.versionLabel}（${activeVersion.publisherName} 于 ${activeVersion.publishedAt} 发布）。\n\n是否以最新版本为基准重新确认？`
    : '当前已无生效版本（可能被他人取消）。是否重新确认后发布？'
  try {
    await ElMessageBox.confirm(text, '生效版本已变更', {
      type: 'warning',
      confirmButtonText: '重新确认',
      cancelButtonText: '取消',
    })
    return true
  } catch {
    return false
  }
}

/** 4004 发布校验失败：按 reasons 汇总展示，行级问题返回其 id 供页面高亮 */
export async function showPublishReasons(data: unknown): Promise<{ itemIds: string[]; stepIds: string[] }> {
  const reasons = asReasons(data) as PublishReason[]
  const lines = reasons.map((r) => {
    const where = r.scope === 'header' ? '' : `第 ${r.lineNo ?? '?'} 行：`
    return `· ${where}${r.message}`
  })
  await ElMessageBox.alert(
    lines.length ? `发布校验未通过：\n\n${lines.join('\n')}\n\n草稿与现有生效版本均已保留，请修正后再发布。` : '发布校验未通过，请检查配置后重试。',
    '无法发布',
    { type: 'warning', confirmButtonText: '知道了' },
  )
  return {
    itemIds: reasons.filter((r) => r.scope === 'item' && r.itemId).map((r) => r.itemId as string),
    stepIds: reasons.filter((r) => r.scope === 'step' && r.stepId).map((r) => r.stepId as string),
  }
}

/** 4003 引用清单（档案停用/取消可生产标志时用，版本页一般不会遇到） */
export function referenceLines(refs: ReferenceItem[]): string {
  if (!refs.length) return '存在生效配置引用。'
  return refs
    .map((r) => `· ${r.configType === 'BOM' ? 'BOM' : '工艺路线'} ${r.productCode} ${r.productName}（${r.version}）`)
    .join('\n')
}

/** 版本状态下拉文案 */
export function versionStatusText(status: VersionBrief['status']): string {
  return status === '0' ? '草稿' : status === '1' ? '生效' : '历史'
}
