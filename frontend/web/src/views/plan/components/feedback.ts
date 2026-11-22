// 计划管理错误反馈：按契约-计划管理 §5.1 的结构化 data 分流。
// 请求层已统一弹 message，这里只做「需要用户进一步操作」的结构化提示。
import { ElMessageBox } from 'element-plus'
import { PLAN_BIZ_CODE } from '@/constants/biz'
import { ApiError } from '@/api/request'
import type {
  GanttErrorsData, MissingDefinitionData, QuantityConflictData, StateConflictData,
} from '@/types'

export function asMissingDefinition(data: unknown): MissingDefinitionData | null {
  const d = data as MissingDefinitionData | undefined
  return d?.productId && Array.isArray(d.missingItems) ? d : null
}
export function asQuantityConflict(data: unknown): QuantityConflictData | null {
  const d = data as QuantityConflictData | undefined
  return d?.orderItemId ? d : null
}
export function asGanttErrors(data: unknown): GanttErrorsData['errors'] {
  return (data as GanttErrorsData | undefined)?.errors ?? []
}
export function asStateConflict(data: unknown): StateConflictData['reason'] | null {
  return (data as StateConflictData | undefined)?.reason ?? null
}

/** 猜测码的中文兜底（后端给 message 优先；这里按稳定 code 兜底） */
export const REASON_FALLBACK: Record<string, string> = {
  ORDER_CANCELLED: '订单已取消',
  ORDER_HAS_ACTIVE_PLANS: '存在有效计划，禁止该操作',
  NO_AVAILABLE_QTY: '无可排数量',
  PLAN_CANCELLED: '计划已取消',
  PLAN_ALREADY_TRANSFERRED: '计划已转单',
  MISSING_PRODUCTION_DEFINITION: '缺少生效 BOM 或工艺路线',
}

export function reasonText(reason: { code: string; message: string } | null | undefined): string {
  if (!reason) return '当前业务状态下不可操作'
  return reason.message || REASON_FALLBACK[reason.code] || reason.code
}

/** 缺生产定义：列出缺失项，提示去基础数据配置 */
export async function showMissingDefinition(data: unknown, productName?: string): Promise<boolean> {
  const d = asMissingDefinition(data)
  const items = d?.missingItems.map((m) => (m === 'BOM' ? 'BOM' : '工艺路线')).join('、') || '生产定义'
  try {
    await ElMessageBox.confirm(
      `产品${productName ? `「${productName}」` : ''}缺少生效的${items}，无法转单。生产计划已保留。\n\n请先在基础数据中配置并发布对应版本后重试。`,
      '缺少生产定义',
      { type: 'warning', confirmButtonText: '知道了', cancelButtonText: '去配置', distinguishCancelAndClose: true },
    )
    return false
  } catch (e) {
    // 点"去配置"= 返回 true，由调用方跳转
    return e === 'cancel'
  }
}

/** 判断是否计划管理的两项字符串冲突码 */
export function isPlanStringConflict(code: number | string): boolean {
  return code === PLAN_BIZ_CODE.MISSING_PRODUCTION_DEFINITION
    || code === PLAN_BIZ_CODE.PLAN_QUANTITY_EXCEEDS_AVAILABLE
}

/** 甘特图日期倒序（400 + 1001）：取出 field=dateEnd 的提示文案 */
export function ganttDateError(data: unknown): string {
  const errs = asGanttErrors(data)
  const e = errs.find((x) => x.field === 'dateEnd') ?? errs[0]
  return e?.message || '结束日期不能早于开始日期'
}

export { ApiError }
