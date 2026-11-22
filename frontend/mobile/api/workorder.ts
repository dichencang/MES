// 生产工单只读接口（移动端首期只做列表与详情）。
// 复用 Web 同一套 API，路径与契约-生产工单一致；权限为 workorder:list。
import { get } from '../utils/request'
import type { PageResult } from '../types'

/** 工单列表行（只读所需字段） */
export interface WorkOrderRowM {
  id: string
  workOrderNo: string
  productCode: string
  productName: string
  unitName: string
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  status: string
  planNo: string | null
  releasedAt: string | null
  startedAt: string | null
  stepCount: number
  finishedStepCount: number | null
}

export interface WorkOrderStepM {
  id: string
  seq: number
  processCode: string
  processName: string
  canAssign: boolean
  assignees: Array<{ id: string; assigneeName: string; endedAt: string | null }>
}

export interface WorkOrderDetailM extends WorkOrderRowM {
  remark: string | null
  cancelReason: string | null
  steps: WorkOrderStepM[]
}

export function listWorkOrders(params: Record<string, unknown>) {
  return get<PageResult<WorkOrderRowM>>('/workorders', params)
}

export function getWorkOrder(id: string) {
  return get<WorkOrderDetailM>('/workorders/' + id)
}

/** 状态文案（与契约 §4.1 一致，移动端独立常量，勿与订单状态混用） */
export const WO_STATUS_LABEL: Record<string, string> = {
  PENDING_RELEASE: '待下发',
  RELEASED: '已下发',
  IN_PRODUCTION: '生产中',
  COMPLETED: '已完成',
  CLOSED: '已关闭',
  CANCELLED: '已撤销',
}
