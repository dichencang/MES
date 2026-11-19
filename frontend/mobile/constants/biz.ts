// 业务码，与 Web 端 constants/biz.ts 保持一致（登录图片验证码契约）。
// 一律按 code 分流，不猜 message。
export const BIZ_CODE = {
  OK: 0,
  INVALID_PARAM: 1001,
  TOKEN_EXPIRED: 2001,
  SESSION_INVALID: 2002,
  REFRESH_INVALID: 2003,
  BAD_CREDENTIALS: 2004,
  CAPTCHA_INVALID: 2005,
  REDIS_UNAVAILABLE: 9002,
  CAPTCHA_TOO_FREQUENT: 9003,
} as const

// 本地错误码：网络异常 / 超时
export const LOCAL_CODE = {
  NETWORK: -1,
  TIMEOUT: -2,
} as const
