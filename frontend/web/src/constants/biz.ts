// 后端业务码。与「登录图片验证码增量契约」一致，前端一律按码分流，不猜 message。
// 约定：业务错误都走非 2xx HTTP 状态，code 与 message 随响应体返回，message 可直接展示。
export const BIZ_CODE = {
  OK: 0,
  /** 请求参数校验失败（含验证码字段缺失/格式不合法） */
  INVALID_PARAM: 1001,
  /** 访问令牌过期，或旧令牌对应的会话已被刷新轮换 —— 有新令牌时换新令牌重放一次 */
  TOKEN_EXPIRED: 2001,
  /** 永久失效：账号停用 / 删除 / 改密 / 主动退出 —— 清会话并跳登录 */
  SESSION_INVALID: 2002,
  /** 刷新令牌无效或过期 */
  REFRESH_INVALID: 2003,
  /** 账号或密码错误 */
  BAD_CREDENTIALS: 2004,
  /** 验证码错误、过期或已使用 */
  CAPTCHA_INVALID: 2005,
  /** Redis 不可用（取图与登录均可能返回） */
  REDIS_UNAVAILABLE: 9002,
  /** 获取验证码过于频繁（HTTP 429） */
  CAPTCHA_TOO_FREQUENT: 9003,
} as const

export type BizCode = (typeof BIZ_CODE)[keyof typeof BIZ_CODE]

/** 计划管理专用字符串业务码（HTTP 409，契约-计划管理 §5.1）。与数字码分开，避免混淆 */
export const PLAN_BIZ_CODE = {
  MISSING_PRODUCTION_DEFINITION: 'MISSING_PRODUCTION_DEFINITION',
  PLAN_QUANTITY_EXCEEDS_AVAILABLE: 'PLAN_QUANTITY_EXCEEDS_AVAILABLE',
  /** 其余状态冲突：HTTP 409 + 数字码 + data.reason */
  STATE_CONFLICT: 4100,
} as const

/** 生产工单专用字符串业务码（HTTP 409，契约-生产工单 §五）。状态冲突沿用数字 4100 */
export const WORK_ORDER_BIZ_CODE = {
  MISSING_PRODUCTION_DEFINITION: 'MISSING_PRODUCTION_DEFINITION',
  WORK_ORDER_QUANTITY_INVALID: 'WORK_ORDER_QUANTITY_INVALID',
  STATE_CONFLICT: 4100,
} as const

/** 工单动作禁用原因兜底文案（契约 §4.3）；后端给 message 优先，此处仅兜底 */
export const WO_REASON_FALLBACK: Record<string, string> = {
  WORK_ORDER_CANCELLED: '工单已撤销',
  WORK_ORDER_NOT_RELEASED: '工单尚未下发',
  WORK_ORDER_ALREADY_RELEASED: '工单已下发，不可修改或重复下发',
  WORK_ORDER_ALREADY_STARTED: '工单已开工，不可重复开工或撤销',
  WORK_ORDER_STEP_STARTED: '该工序已开工，不可改派',
  WORK_ORDER_HAS_WIP: '存在在制量未处置',
  WORK_ORDER_NOT_STARTED: '工单未开工',
  WORK_ORDER_TERMINAL: '工单已完成或已关闭',
  PLAN_LINKED_WORK_ORDER: '来源计划工单，不可编辑',
  PLAN_CANCELLED: '来源计划已取消',
  WORK_ORDER_SETTLEMENT_DISABLED: '完工及关闭尚未开放',
}

/** 前端本地错误码：网络异常 / 超时时使用，不与后端码冲突 */export const LOCAL_CODE = {
  NETWORK: -1,
  TIMEOUT: -2,
} as const
