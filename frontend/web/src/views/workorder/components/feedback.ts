// 工单错误反馈（契约-生产工单 §五）。请求层已统一弹 message，这里只做需要用户进一步操作的结构化提示。
import { ElMessageBox } from 'element-plus'
import { WORK_ORDER_BIZ_CODE } from '@/constants/biz'
import { ApiError } from '@/api/request'
import type { WorkOrderReason } from '@/types'

export interface MissingDefinitionData { productId: string; missingItems: Array<'BOM' | 'ROUTING'> }
export interface QuantityInvalidData {
  field: string
  materialId: string
  sourceBomItemId: string
  reason: 'ROUNDED_TO_ZERO' | 'OVERFLOW'
}
export interface ParamErrorsData { errors: Array<{ field: string; message: string }> }

export function asMissingDefinition(data: unknown): MissingDefinitionData | null {
  const d = data as MissingDefinitionData | undefined
  return d?.productId && Array.isArray(d.missingItems) ? d : null
}

export function asQuantityInvalid(data: unknown): QuantityInvalidData | null {
  const d = data as QuantityInvalidData | undefined
  return d?.reason ? d : null
}

/** 参数错误：取指定字段的第一条 message（字段未命中时取首条） */
export function paramError(data: unknown, field?: string): string {
  const errs = (data as ParamErrorsData | undefined)?.errors ?? []
  const hit = field ? errs.find((e) => e.field === field) : undefined
  return (hit ?? errs[0])?.message || '参数校验失败'
}

/** 能力禁用原因 → 可读文案（后端 message 优先，前端按稳定 code 兜底） */
export function reasonText(reason: WorkOrderReason | null | undefined): string {
  if (!reason) return '当前状态下不可操作'
  return reason.message || reason.code
}

/** 缺生效版本：列出缺失项，提供"去配置"入口 */
export async function showMissingDefinition(data: unknown): Promise<boolean> {
  const d = asMissingDefinition(data)
  const items = d?.missingItems.map((m) => (m === 'BOM' ? 'BOM' : '工艺路线')).join('、') || '生产定义'
  try {
    await ElMessageBox.confirm(
      `该产品缺少生效的${items}，无法创建或转成工单。\n\n请先在基础数据中配置并发布对应版本后重试。`,
      '缺少生产定义',
      { type: 'warning', confirmButtonText: '知道了', cancelButtonText: '去配置', distinguishCancelAndClose: true },
    )
    return false
  } catch (e) {
    return e === 'cancel'
  }
}

/** 子件需求量异常（舍零/溢出）：指出具体子件，提示整单未保存 */
export async function showQuantityInvalid(data: unknown): Promise<void> {
  const d = asQuantityInvalid(data)
  const why = d?.reason === 'OVERFLOW' ? '需求量超出字段上限' : '需求量四舍五入后为零'
  await ElMessageBox.alert(
    `按当前工单数量计算的子件${why}（物料 ID：${d?.materialId ?? '—'}），本次保存已整单取消。\n\n请调整计划数量后重试。`,
    '子件需求量异常',
    { type: 'warning', confirmButtonText: '知道了' },
  )
}

export { ApiError, WORK_ORDER_BIZ_CODE }
