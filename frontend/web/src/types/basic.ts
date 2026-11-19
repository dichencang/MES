// 基础数据模块类型。字段与《契约-基础数据-最终版》v1.2 一致：
//   camelCase / ID 字符串 / status 为 "0"·"1"（版本三态为 "0"·"1"·"2"）
//   **数量一律十进制字符串**（"8.0000"），后端按 numeric(18,4) 序列化，前端不做浮点运算。

/** 启停状态："0" 启用 / "1" 停用 */
export type EnabledStatus = '0' | '1'
/** 版本状态："0" 草稿 / "1" 生效 / "2" 历史 */
export type VersionStatus = '0' | '1' | '2'
/** 聚合列表筛选：三值互斥 */
export type ConfigStatusFilter = 'all' | 'configured' | 'draft-only' | 'unconfigured'

// ── 档案 ───────────────────────────────────────────────
export interface Material {
  id: string
  code: string
  name: string
  categoryCode: string
  categoryLabel: string
  spec: string | null
  unitCode: string
  unitName: string
  status: EnabledStatus
  isProduct: boolean
  remark: string | null
}

export interface MaterialQuery {
  keyword?: string
  categoryCode?: string
  status?: EnabledStatus
  isProduct?: boolean
  page: number
  pageSize: number
}

/** 新建物料（code/unitCode 建后不可改） */
export interface MaterialCreatePayload {
  code: string
  name: string
  categoryCode: string
  spec: string | null
  unitCode: string
  isProduct: boolean
  remark: string | null
}

/** 编辑物料（不含 code/unitCode，携带会被 400 拒绝） */
export type MaterialUpdatePayload = Omit<MaterialCreatePayload, 'code' | 'unitCode'>

export interface Process {
  id: string
  code: string
  name: string
  description: string | null
  status: EnabledStatus
}

export interface ProcessQuery {
  keyword?: string
  status?: EnabledStatus
  page: number
  pageSize: number
}

export interface ProcessCreatePayload {
  code: string
  name: string
  description: string | null
}
export type ProcessUpdatePayload = Omit<ProcessCreatePayload, 'code'>

// ── 版本通用 ───────────────────────────────────────────
/** 版本摘要：详情 versions[] / 聚合 latestDraft。**不含 draftToken** */
export interface VersionBrief {
  id: string
  version: number
  versionLabel: string
  status: VersionStatus
  publishedAt: string | null
  createTime: string
}

/** 生效版本摘要 */
export interface ActiveVersion {
  id: string
  version: number
  versionLabel: string
  publishedAt: string
  publisherName: string
}

/** 聚合列表行：BOM 与路线共用 */
export interface ConfigProductRow {
  productId: string
  productCode: string
  productName: string
  /** 产品（物料）当前状态，停用时隐藏「新建」入口 */
  productStatus: EnabledStatus
  spec: string | null
  unitName: string
  activeVersion: ActiveVersion | null
  latestDraft: VersionBrief | null
  /** 全部保留版本数（草稿+生效+历史） */
  versionCount: number
  /** 无任何配置时为 null */
  updateTime: string | null
}

export interface ConfigProductQuery {
  keyword?: string
  configStatus?: ConfigStatusFilter
  page: number
  pageSize: number
}

/** 新建/复制请求体：不带 sourceVersionId = 空白新建 */
export interface VersionCreatePayload {
  productId: string
  sourceVersionId?: string
}

// ── BOM ───────────────────────────────────────────────
export interface BomItem {
  itemId: string
  materialId: string
  /** 引用展示字段，取主数据当前值 */
  materialCode: string
  materialName: string
  /** 子件当前启停状态；停用子件仍回显 */
  materialStatus: EnabledStatus
  unitName: string
  /** "8.0000" 十进制字符串 */
  qty: string
  /** 后端下发则按其排序；不下发按数组顺序 */
  sortNo?: number
}

export interface BomVersion {
  id: string
  productId: string
  productCode: string
  productName: string
  version: number
  versionLabel: string
  status: VersionStatus
  baseQty: string
  /** 仅草稿非空；生效/历史为 null */
  draftToken: string | null
  items: BomItem[]
  activeVersion: ActiveVersion | null
  versions: VersionBrief[]
  createTime: string
  updateTime: string
  lastEditorName: string
}

/** 保存明细入参：**绝不带 sortNo**（带了返回 400+1001） */
export interface BomItemInput {
  itemId?: string
  materialId: string
  qty: string
}

export interface BomSavePayload {
  draftToken: string
  baseQty: string
  items: BomItemInput[]
}

// ── 工艺路线 ───────────────────────────────────────────
export interface RoutingStep {
  stepId: string
  seq: number
  processId: string
  processCode: string
  processName: string
  processStatus: EnabledStatus
  remark: string | null
}

export interface RoutingVersion {
  id: string
  productId: string
  productCode: string
  productName: string
  version: number
  versionLabel: string
  status: VersionStatus
  draftToken: string | null
  steps: RoutingStep[]
  activeVersion: ActiveVersion | null
  versions: VersionBrief[]
  createTime: string
  updateTime: string
  lastEditorName: string
}

/** 步骤入参：**seq 必须传**（与 BOM 的 sortNo 相反） */
export interface RoutingStepInput {
  stepId?: string
  seq: number
  processId: string
  remark?: string | null
}

export interface RoutingSavePayload {
  draftToken: string
  steps: RoutingStepInput[]
}

// ── 发布 ───────────────────────────────────────────────
export interface PublishPayload {
  draftToken: string
  /** 无生效版本时显式传 null，**不可省略** */
  expectedActiveVersionId: string | null
}

export interface PublishResult {
  id: string
  version: number
  versionLabel: string
  status: VersionStatus
  publishedAt: string
  activeVersion: ActiveVersion | null
}

// ── 公共选项 ───────────────────────────────────────────
export interface MaterialOption {
  id: string
  code: string
  name: string
  spec: string | null
  categoryCode: string
  categoryLabel: string
  unitName: string
  status: EnabledStatus
  isProduct: boolean
}

export interface ProcessOption {
  id: string
  code: string
  name: string
  status: EnabledStatus
}

export interface OptionQuery {
  keyword?: string
  isProduct?: boolean
  status?: EnabledStatus
  page?: number
  pageSize?: number
}

// ── 错误响应附加数据 ───────────────────────────────────
/** 4003：停用/取消可生产被生效配置引用 */
export interface ReferenceItem {
  configType: 'BOM' | 'ROUTING'
  productCode: string
  productName: string
  version: string
  versionStatus: string
}
export interface ReferencesData {
  references: ReferenceItem[]
}

/** 4004：发布校验失败，按 scope 定位 */
export interface PublishReason {
  scope: 'item' | 'step' | 'header'
  /** scope=item 时用于高亮行 */
  itemId?: string
  /** scope=step 时用于高亮行 */
  stepId?: string
  /** 行号，仅用于文案 */
  lineNo?: number
  /** scope=header 时用于定位表头字段 */
  field?: string
  code: string
  message: string
}
export interface ReasonsData {
  reasons: PublishReason[]
}

/** 4001：草稿并发冲突 */
export interface DraftConflictData {
  lastEditorName: string
  lastUpdatedAt: string
}

/** 4002：发布时生效版本已变更 */
export interface ActiveChangedData {
  activeVersion: ActiveVersion | null
}
