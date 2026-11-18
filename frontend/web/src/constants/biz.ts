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

/** 前端本地错误码：网络异常 / 超时时使用，不与后端码冲突 */
export const LOCAL_CODE = {
  NETWORK: -1,
  TIMEOUT: -2,
} as const
