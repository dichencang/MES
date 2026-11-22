// 计划管理接口。路径与字段严格对照 docs/契约-计划管理-最终版.md（权威契约）。
// 要点：
//   · 数量一律十进制字符串，不做浮点转换
//   · 时间用 ISO 8601 UTC Z，页面按 Asia/Shanghai 展示
//   · 两项业务冲突为 HTTP 409 + 字符串 code，结构化字段在 data；Web ApiError.code 已放宽为 number|string
import { get, post, put } from '../request'
import type {
  CancelPayload, CreateOrderResult, CreatePlanResult, GanttPlan,
  OrderItemCandidate, PageResult, ProductionPlanDetail, ProductionPlanRow,
  SalesOrderDetail, SalesOrderRow, SalesOrderSavePayload, PlanCreatePayload, PlanUpdatePayload,
} from '@/types'

// ── 销售订单 ───────────────────────────────────────────
export const listSalesOrders = (params: Record<string, unknown>) =>
  get<PageResult<SalesOrderRow>>('/plan/sales-orders', params)
export const getSalesOrder = (id: string) => get<SalesOrderDetail>(`/plan/sales-orders/${id}`)
export const createSalesOrder = (data: SalesOrderSavePayload) =>
  post<CreateOrderResult>('/plan/sales-orders', data)
export const updateSalesOrder = (id: string, data: SalesOrderSavePayload) =>
  put<SalesOrderDetail>(`/plan/sales-orders/${id}`, data)
export const cancelSalesOrder = (id: string, data: CancelPayload) =>
  post<SalesOrderDetail>(`/plan/sales-orders/${id}/cancel`, data)
/** 订单行候选：两个拆计划入口共用 */
export const listOrderItems = (params: Record<string, unknown>) =>
  get<PageResult<OrderItemCandidate>>('/plan/sales-order-items', params)

// ── 生产计划 ───────────────────────────────────────────
export const listProductionPlans = (params: Record<string, unknown>) =>
  get<PageResult<ProductionPlanRow>>('/plan/production-plans', params)
export const getProductionPlan = (id: string) => get<ProductionPlanDetail>(`/plan/production-plans/${id}`)
export const createProductionPlan = (data: PlanCreatePayload) =>
  post<CreatePlanResult>('/plan/production-plans', data)
export const updateProductionPlan = (id: string, data: PlanUpdatePayload) =>
  put<ProductionPlanDetail>(`/plan/production-plans/${id}`, data)
export const cancelProductionPlan = (id: string, data: CancelPayload) =>
  post<ProductionPlanDetail>(`/plan/production-plans/${id}/cancel`, data)
export const transferProductionPlan = (id: string) =>
  post<ProductionPlanDetail>(`/plan/production-plans/${id}/transfer`)

// ── 甘特图 ─────────────────────────────────────────────
export const listGantt = (params: Record<string, unknown>) => get<GanttPlan[]>('/plan/gantt', params)
