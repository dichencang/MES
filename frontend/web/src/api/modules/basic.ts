// 基础数据接口。路径与请求体严格对照《契约-基础数据-最终版》v1.2。
// 要点：
//   · 数量（baseQty/qty）一律十进制字符串，不做浮点转换
//   · BOM 明细提交**不带 sortNo**（后端按下标生成）；路线步骤**必须带 seq**
//   · DELETE 草稿的 draftToken 走 Query
//   · 发布必须同时带 draftToken 与 expectedActiveVersionId（无生效版传 null）
import { del, get, post, put } from '../request'
import type {
  BomSavePayload, BomVersion, ConfigProductRow,
  DraftConflictData, Material, MaterialCreatePayload, MaterialOption,
  MaterialUpdatePayload, PageResult, Process, ProcessCreatePayload,
  ProcessOption, ProcessUpdatePayload, PublishPayload, PublishResult,
  ReasonsData, ReferencesData, RoutingSavePayload, RoutingVersion, VersionCreatePayload,
} from '@/types'

// ── 物料 ───────────────────────────────────────────────
export const listMaterials = (params: Record<string, unknown>) => get<PageResult<Material>>('/materials', params)
export const createMaterial = (data: MaterialCreatePayload) => post<Material>('/materials', data)
/** 编辑不传 code/unitCode（携带会被后端 400 拒绝） */
export const updateMaterial = (id: string, data: MaterialUpdatePayload) => put<Material>(`/materials/${id}`, data)
export const setMaterialStatus = (id: string, status: '0' | '1') => put<null>(`/materials/${id}/status`, { status })

// ── 工序 ───────────────────────────────────────────────
export const listProcesses = (params: Record<string, unknown>) => get<PageResult<Process>>('/processes', params)
export const createProcess = (data: ProcessCreatePayload) => post<Process>('/processes', data)
export const updateProcess = (id: string, data: ProcessUpdatePayload) => put<Process>(`/processes/${id}`, data)
export const setProcessStatus = (id: string, status: '0' | '1') => put<null>(`/processes/${id}/status`, { status })

// ── 产品 BOM ───────────────────────────────────────────
/** 产品维度聚合列表，含未配置的产品 */
export const listBomProducts = (params: Record<string, unknown>) =>
  get<PageResult<ConfigProductRow>>('/boms/products', params)
/** 版本详情（id 为版本 ID） */
export const getBom = (id: string) => get<BomVersion>(`/boms/${id}`)
/** 新建/复制草稿 */
export const createBom = (data: VersionCreatePayload) => post<BomVersion>('/boms', data)
/** 整单保存（全量覆盖），成功后返回新 draftToken 与新 itemId */
export const saveBom = (id: string, data: BomSavePayload) => put<BomVersion>(`/boms/${id}`, data)
export const publishBom = (id: string, data: PublishPayload) => post<PublishResult>(`/boms/${id}/publish`, data)
/** 删除草稿：draftToken 走 Query */
export const deleteBom = (id: string, draftToken: string) => del<null>(`/boms/${id}`, { draftToken })

// ── 工艺路线 ───────────────────────────────────────────
export const listRoutingProducts = (params: Record<string, unknown>) =>
  get<PageResult<ConfigProductRow>>('/routings/products', params)
export const getRouting = (id: string) => get<RoutingVersion>(`/routings/${id}`)
export const createRouting = (data: VersionCreatePayload) => post<RoutingVersion>('/routings', data)
export const saveRouting = (id: string, data: RoutingSavePayload) => put<RoutingVersion>(`/routings/${id}`, data)
export const publishRouting = (id: string, data: PublishPayload) => post<PublishResult>(`/routings/${id}/publish`, data)
export const deleteRouting = (id: string, draftToken: string) => del<null>(`/routings/${id}`, { draftToken })

// ── 公共选项（仅会话校验，不占业务编码）─────────────────
/** 物料候选：父件/路线产品传 isProduct=true；子件候选不传 status（默认仅启用） */
export const materialOptions = (params: Record<string, unknown>) => get<PageResult<MaterialOption>>('/materials/options', params)
/** 工序候选：固定只返回启用项，无 status 参数 */
export const processOptions = (params: Record<string, unknown>) => get<PageResult<ProcessOption>>('/processes/options', params)

// ── 错误数据提取（页面按 code 分流时取）─────────────────
export const asReferences = (data: unknown): ReferencesData['references'] =>
  (data as ReferencesData | undefined)?.references ?? []
export const asReasons = (data: unknown): ReasonsData['reasons'] =>
  (data as ReasonsData | undefined)?.reasons ?? []
export const asDraftConflict = (data: unknown): DraftConflictData | null =>
  (data as DraftConflictData | undefined)?.lastEditorName ? (data as DraftConflictData) : null
