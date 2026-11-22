// 生产工单类型。字段严格对照 docs/契约-生产工单-最终版.md（唯一依据）。
// 约定：camelCase / ID 为字符串 / 数量为四位小数字符串（"12.0000"）/ 时间为 ISO 8601 UTC Z。
// 注意：工单 IN_PRODUCTION 与销售订单 IN_PRODUCTION 同名不同义，标签常量分两套，勿混用。
import type { VersionRef } from './plan'

export type WorkOrderStatus =
  | 'PENDING_RELEASE' | 'RELEASED' | 'IN_PRODUCTION' | 'COMPLETED' | 'CLOSED' | 'CANCELLED'

/** 工单状态文案（契约 §4.1）。与 SALES_ORDER_STATUS_LABEL 刻意分开 */
export const WO_STATUS_LABEL: Record<WorkOrderStatus, string> = {
  PENDING_RELEASE: '待下发',
  RELEASED: '已下发',
  IN_PRODUCTION: '生产中',
  COMPLETED: '已完成',
  CLOSED: '已关闭',
  CANCELLED: '已撤销',
}

/** 能力键（契约 §4.2）：disableReasons 的键与动作同名 */
export type WorkOrderActionKey =
  | 'edit' | 'release' | 'assign' | 'start' | 'cancel' | 'complete' | 'close'

export interface WorkOrderReason { code: string; message: string }

export interface WorkOrderActions {
  canEdit: boolean
  canRelease: boolean
  canAssign: boolean
  canStart: boolean
  canCancel: boolean
  canComplete: boolean
  canClose: boolean
  disableReasons: Partial<Record<WorkOrderActionKey, WorkOrderReason>>
}

/** 列表行（契约 §3.1） */
export interface WorkOrderRow {
  id: string
  workOrderNo: string
  productId: string
  productCode: string
  productName: string
  unitCode: string
  unitName: string
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  status: WorkOrderStatus
  planId: string | null
  planNo: string | null
  releasedAt: string | null
  startedAt: string | null
  stepCount: number
  /** 首期恒 null（后端无事实数据），前端显示"待接入"而非 0 */
  finishedStepCount: number | null
}

/** 用料快照（契约 §3.3） */
export interface WorkOrderMaterial {
  id: string
  materialId: string
  materialCode: string
  materialName: string
  unitCode: string
  unitName: string
  baseQty: string
  componentQty: string
  requiredQty: string
  sortNo: number
  sourceBomItemId: string
}

/** 派工记录（契约 §3.5）：endedAt 为 null 表示当前有效，非空为历史 */
export interface WorkOrderAssignee {
  id: string
  assigneeId: string
  assigneeName: string
  assignedAt: string
  endedAt: string | null
}

/** 工序快照（契约 §3.4） */
export interface WorkOrderStep {
  id: string
  seq: number
  processId: string
  processCode: string
  processName: string
  sourceRoutingStepId: string
  remark: string | null
  canAssign: boolean
  disableReason: WorkOrderReason | null
  assignees: WorkOrderAssignee[]
}

export type WorkOrderEventAction =
  | 'CREATE' | 'TRANSFER' | 'UPDATE' | 'RELEASE' | 'ASSIGN' | 'START' | 'CANCEL' | 'COMPLETE' | 'CLOSE'

export const WO_EVENT_LABEL: Record<WorkOrderEventAction, string> = {
  CREATE: '创建',
  TRANSFER: '计划转单',
  UPDATE: '修改',
  RELEASE: '下发',
  ASSIGN: '派工',
  START: '开工',
  CANCEL: '撤销',
  COMPLETE: '完工',
  CLOSE: '关闭',
}

/** 事件（契约 §3.6）：CREATE 的 fromStatus 为 null */
export interface WorkOrderEvent {
  id: string
  action: WorkOrderEventAction
  fromStatus: WorkOrderStatus | null
  toStatus: WorkOrderStatus
  operatorName: string
  occurredAt: string
  reason: string | null
}

/** 详情（契约 §3.2） */
export interface WorkOrderDetail extends WorkOrderRow {
  remark: string | null
  bomVersion: VersionRef | null
  routingVersion: VersionRef | null
  /** 首期恒 null */
  currentStepId: string | null
  actions: WorkOrderActions
  materials: WorkOrderMaterial[]
  steps: WorkOrderStep[]
  /** 最近 10 条 */
  events: WorkOrderEvent[]
  cancelledAt: string | null
  cancelledBy: string | null
  cancelReason: string | null
  closedAt: string | null
  closedBy: string | null
  closeReason: string | null
}

/** 甘特条目（契约 §3.7） */
export interface GanttWorkOrder {
  id: string
  workOrderNo: string
  productName: string
  plannedStartAt: string
  plannedEndAt: string
  status: WorkOrderStatus
  planNo: string | null
}

/** 派工候选（契约 §3.8） */
export interface AssigneeOption {
  id: string
  username: string
  realName: string
}

// ── 请求体 ─────────────────────────────────────────────
export interface WorkOrderCreatePayload {
  productId: string
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  remark?: string | null
}
export interface WorkOrderUpdatePayload {
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  remark: string | null
}
export interface WorkOrderCreateResult { id: string; workOrderNo: string }
export interface AssigneesPayload { assigneeIds: string[] }
