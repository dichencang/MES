// 认证与会话：图片验证码、登录、登出、当前用户、当前权限树、自助改密。
// 登录请求必带 captchaId + captchaCode（见「登录图片验证码增量契约」）。
import { get, post, put, tokenStore } from '../request'
import type { AuthSession, CaptchaResult, LoginPayload, MyPermissions, UserInfo } from '@/types'

/** 取图形验证码。无需登录；加时间戳参数双保险，避免浏览器缓存旧图 */
export const getCaptcha = () => get<CaptchaResult>('/auth/captcha', { t: Date.now() })

export const login = (payload: LoginPayload) => post<AuthSession>('/auth/login', payload)

export const logout = () => post<null>('/auth/logout', { refreshToken: tokenStore.refresh })

export const getMe = () => get<UserInfo>('/auth/me')

export const changeOwnPassword = (oldPassword: string, newPassword: string) =>
  put<null>('/users/me/password', { oldPassword, newPassword })

/** 登录后拉取：嵌套导航树（DIR/MENU）+ 扁平权限编码（含 BUTTON） */
export const getMyPermissions = () => get<MyPermissions>('/permissions/my')
