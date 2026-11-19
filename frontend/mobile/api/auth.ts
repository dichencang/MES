// 认证接口。路径与错误码对照 Web 端 api/modules/auth.ts，同一后端一套 API。
import { get, post } from '../utils/request'
import { tokenStore } from '../utils/auth'
import type { AuthSession, CaptchaResult, LoginPayload, MyPermissions, UserInfo } from '../types'

/** 图片验证码。无需登录，加时间戳参数避免缓存 */
export function getCaptcha(): Promise<CaptchaResult> {
  return get<CaptchaResult>('/auth/captcha', { t: Date.now() }, false)
}

export function login(payload: LoginPayload): Promise<AuthSession> {
  return post<AuthSession>('/auth/login', payload, false)
}

export function logout(): Promise<null> {
  return post<null>('/auth/logout', { refreshToken: tokenStore.refresh }, false)
}

export function getMe(): Promise<UserInfo> {
  return get<UserInfo>('/auth/me')
}

export function getMyPermissions(): Promise<MyPermissions> {
  return get<MyPermissions>('/permissions/my')
}
