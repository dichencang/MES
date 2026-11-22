// 生产工单接口。路径与字段严格对照 docs/契约-生产工单-最终版.md（权威契约）。
// 要点：
//   · 路径统一 /workorders/*（静态子路径 /gantt、/assignee-options 由后端保证先注册）
//   · 数量一律十进制字符串；时间 ISO 8601 UTC Z
//   · 业务冲突：409 + 字符串码（MISSING_PRODUCTION_DEFINITION / WORK_ORDER_QUANTITY_INVALID）、
//     409 + 数字 4100（状态冲突，data.reason）、400 + 1001（参数，data.errors）
import { get, post, put } from '../request'
import type {
  AssigneeOption, AssigneesPayload, GanttWorkOrder, PageResult,
  WorkOrderCreatePayload, WorkOrderCreateResult, WorkOrderDetail, WorkOrderEvent,
  WorkOrderRow, WorkOrderUpdatePayload,
} from '@/types'

export const listWorkOrders = (params: Record<string, unknown>) =>
  get<PageResult<WorkOrderRow>>('/workorders', params)
export const getWorkOrder = (id: string) => get<WorkOrderDetail>(`/workorders/${id}`)
export const createWorkOrder = (data: WorkOrderCreatePayload) =>
  post<WorkOrderCreateResult>('/workorders', data)
export const updateWorkOrder = (id: string, data: WorkOrderUpdatePayload) =>
  put<WorkOrderDetail>(`/workorders/${id}`, data)

// ── 动作（均返回最新详情）──────────────────────────────
export const releaseWorkOrder = (id: string) => post<WorkOrderDetail>(`/workorders/${id}/release`)
export const startWorkOrder = (id: string) => post<WorkOrderDetail>(`/workorders/${id}/start`)
export const cancelWorkOrder = (id: string, data: { cancelReason: string }) =>
  post<WorkOrderDetail>(`/workorders/${id}/cancel`, data)
/** 整步全量替换：空数组＝清除预派，相同集合重复提交无副作用 */
export const setStepAssignees = (id: string, stepId: string, data: AssigneesPayload) =>
  put<WorkOrderDetail>(`/workorders/${id}/steps/${stepId}/assignees`, data)

// ── 辅助查询 ───────────────────────────────────────────
export const listAssigneeOptions = (params: Record<string, unknown>) =>
  get<PageResult<AssigneeOption>>('/workorders/assignee-options', params)
export const listWorkOrderEvents = (id: string, params: Record<string, unknown>) =>
  get<PageResult<WorkOrderEvent>>(`/workorders/${id}/events`, params)
export const listWorkOrderGantt = (params: Record<string, unknown>) =>
  get<GanttWorkOrder[]>('/workorders/gantt', params)
