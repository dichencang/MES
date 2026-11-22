// 计划管理只读接口（移动端首期只做销售订单/生产计划列表与详情）。
// 复用 Web 同一套 API，路径与契约-计划管理一致；权限为计划业务读取权限（非基础数据权限）。
import { get } from '../utils/request'
import type { PageResult } from '../types'

/** 销售订单列表行（只读所需字段） */
export interface SalesOrderRowM {
  id: string
  orderNo: string
  customerName: string
  orderDate: string
  status: string
  itemCount: number
  scheduledItemCount: number
}
export interface SalesOrderItemM {
  id: string
  lineNo: number
  productCode: string
  productName: string
  productStatus: string
  unitName: string
  orderQty: string
  dueDate: string
  scheduledQty: string
  availableQty: string
  completedQty: string
}
export interface SalesOrderDetailM {
  id: string
  orderNo: string
  customerName: string
  orderDate: string
  status: string
  remark: string | null
  items: SalesOrderItemM[]
}
/** 生产计划列表行 */
export interface ProductionPlanRowM {
  id: string
  planNo: string
  orderNo: string
  productName: string
  plannedQty: string
  plannedStartAt: string
  plannedEndAt: string
  status: string
  workOrderNo: string | null
}
export interface ProductionPlanDetailM extends ProductionPlanRowM {
  orderItemId: string
  productCode: string
  unitCode: string
  unitName: string
  remark: string | null
  bomVersion: { id: string; version: number } | null
  routingVersion: { id: string; version: number } | null
  workOrder: { id: string; workOrderNo: string } | null
}

export function listSalesOrders(params: Record<string, unknown>) {
  return get<PageResult<SalesOrderRowM>>('/plan/sales-orders', params)
}
export function getSalesOrder(id: string) {
  return get<SalesOrderDetailM>(`/plan/sales-orders/${id}`)
}
export function listProductionPlans(params: Record<string, unknown>) {
  return get<PageResult<ProductionPlanRowM>>('/plan/production-plans', params)
}
export function getProductionPlan(id: string) {
  return get<ProductionPlanDetailM>(`/plan/production-plans/${id}`)
}

/** 状态文案（与契约一致） */
export const ORDER_STATUS_LABEL: Record<string, string> = {
  CANCELLED: '已取消', COMPLETED: '已完成', IN_PRODUCTION: '生产中',
  SCHEDULED: '已排产', PENDING_SCHEDULING: '待排产',
}
export const PLAN_STATUS_LABEL: Record<string, string> = {
  PENDING_TRANSFER: '待转单', TRANSFERRED: '已转单', CANCELLED: '已取消',
}
