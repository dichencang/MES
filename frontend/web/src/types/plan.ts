// 计划管理模块类型。字段以 `docs/契约-计划管理-最终版.md` 为唯一依据（该文件是权威契约，本文件只是它的 TS 投影）：
//   camelCase / ID 字符串 / 数量一律十进制字符串（"12.0000"）/ 时间为 ISO 8601 UTC Z。
//   契约变更时先改文档、再同步本文件，禁止反过来。

import type { EnabledStatus } from './basic'

// ── 状态枚举 ───────────────────────────────────────────
/** 订单状态：优先级 CANCELLED > COMPLETED > IN_PRODUCTION > SCHEDULED > PENDING_SCHEDULING */
export type SalesOrderStatus =
  | 'CANCELLED' | 'COMPLETED' | 'IN_PRODUCTION' | 'SCHEDULED' | 'PENDING_SCHEDULING'
/** 计划状态：只表达转单进度，工单执行进度由工单模块提供 */
export type ProductionPlanStatus = 'PENDING_TRANSFER' | 'TRANSFERRED' | 'CANCELLED'

export const SALES_ORDER_STATUS_LABEL: Record<SalesOrderStatus, string> = {
  CANCELLED: '已取消',
  COMPLETED: '已完成',
  IN_PRODUCTION: '生产中',
  SCHEDULED: '已排产',
  PENDING_SCHEDULING: '待排产',
}
export const PLAN_STATUS_LABEL: Record<ProductionPlanStatus, string> = {
  PENDING_TRANSFER: '待转单',
  TRANSFERRED: '已转单',
  CANCELLED: '已取消',
}

// ── 原因对象与能力 ─────────────────────────────────────
/** 可操作时为 null；后端给 message，前端按 code 兜底 */
export interface DisableReason {
  code: string
  message: string
}
export type ReasonOrNull = DisableReason | null

export interface SalesOrderActions {
  canEdit: boolean
  canCancel: boolean
  canCreatePlan: boolean
  disableReasons: Partial<Record<'edit' | 'cancel' | 'createPlan', DisableReason>>
}

export interface ProductionPlanActions {
  canReschedule: boolean
  canCancel: boolean
  canTransfer: boolean
  disableReasons: Partial<Record<'reschedule' | 'cancel' | 'transfer', DisableReason>>
}

// ── 销售订单 ───────────────────────────────────────────
export interface SalesOrderRow {
  id: string
  orderNo: string
  customerName: string
  orderDate: string
  status: SalesOrderStatus
  itemCount: number
  scheduledItemCount: number
  createdAt: string
}

/** 订单明细行：编码/名称取订单行快照，状态取当前物料 */
export interface SalesOrderItem {
  id: string // = orderItemId
  lineNo: number
  productId: string
  productCode: string
  productName: string
  productStatus: EnabledStatus
  unitCode: string
  unitName: string
  orderQty: string
  dueDate: string
  scheduledQty: string
  availableQty: string
  completedQty: string
  canCreatePlan: boolean
  disableReason: ReasonOrNull
}

/** 详情字段独立定义：不含列表行的 itemCount / scheduledItemCount / createdAt（契约 §2.2） */
export interface SalesOrderDetail {
  id: string
  orderNo: string
  customerName: string
  orderDate: string
  status: SalesOrderStatus
  remark: string | null
  actions: SalesOrderActions
  cancelledAt: string | null
  cancelledBy: string | null
  cancelReason: string | null
  items: SalesOrderItem[]
}

/** 订单行提交：PUT 既有行带 id；整单全量提交 */
export interface SalesOrderItemInput {
  id?: string
  lineNo: number
  productId: string
  orderQty: string
  dueDate: string
}
export interface SalesOrderSavePayload {
  customerName: string
  orderDate: string
  remark: string | null
  items: SalesOrderItemInput[]
}
export interface CreateOrderResult {
  id: string
  orderNo: string
}

// ── 订单行候选（两入口共用）─────────────────────────────
export interface OrderItemCandidate {
  orderItemId: string
  orderId: string
  orderNo: string
  lineNo: number
  dueDate: string
  orderQty: string
  scheduledQty: string
  availableQty: string
  productId: string
  productCode: string
  productName: string
  unitCode: string
  unitName: string
  canCreatePlan: boolean
  disableReason: ReasonOrNull
}

// ── 生产计划 ───────────────────────────────────────────
export interface ProductionPlanRow {
  id: string
  planNo: string
  orderNo: string
  productName: string
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  status: ProductionPlanStatus
  workOrderNo: string | null
  /** 列表与详情同样下发，可空（契约 §3.1） */
  bomVersion: VersionRef | null
  routingVersion: VersionRef | null
}

/** BOM / 路线版本摘要（工单侧提供，可空） */
export interface VersionRef {
  id: string
  version: number
}

export interface ProductionPlanDetail extends ProductionPlanRow {
  orderItemId: string
  productCode: string
  unitCode: string
  unitName: string
  remark: string | null
  actions: ProductionPlanActions
  features: { workOrderTransferEnabled: boolean }
  /** 无有效关联工单时为 null */
  workOrder: { id: string; workOrderNo: string } | null
  bomVersion: VersionRef | null
  routingVersion: VersionRef | null
  cancelledAt: string | null
  cancelledBy: string | null
  cancelReason: string | null
}

export interface PlanCreatePayload {
  orderItemId: string
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  remark?: string | null
}
export interface PlanUpdatePayload {
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  remark: string | null
}
export interface CreatePlanResult {
  id: string
  planNo: string
}

// ── 取消 ───────────────────────────────────────────────
export interface CancelPayload {
  cancelReason: string
}

// ── 甘特图 ─────────────────────────────────────────────
export interface GanttPlan {
  planId: string
  planNo: string
  orderNo: string
  productName: string
  startAt: string
  endAt: string
  status: ProductionPlanStatus
  workOrderNo: string | null
}
export interface GanttQuery {
  dateStart: string
  dateEnd: string
  productId?: string
}

// ── 错误响应结构化 data ────────────────────────────────
/** 409 MISSING_PRODUCTION_DEFINITION */
export interface MissingDefinitionData {
  productId: string
  missingItems: Array<'BOM' | 'ROUTING'>
}
/** 409 PLAN_QUANTITY_EXCEEDS_AVAILABLE */
export interface QuantityConflictData {
  orderItemId: string
  orderQty: string
  scheduledQty: string
  availableQty: string
}
/** HTTP 400 + 1001 甘特图日期倒序 */
export interface GanttErrorsData {
  errors: Array<{ field: string; message: string }>
}
/** HTTP 409 + 4100 其余状态冲突 */
export interface StateConflictData {
  reason: DisableReason
}
