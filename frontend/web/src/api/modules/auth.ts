// 认证与会话：登录/刷新/登出/当前用户/当前权限树/自助改密。
// 除 login/refresh 外均走 Bearer 令牌，由请求层统一注入。
import { get, post, put, tokenStore } from '../request'
import type { AuthSession, MyPermissions, UserInfo } from '@/types'

export const login = (username: string, password: string) =>
  post<AuthSession>('/auth/login', { username, password })

export const logout = () => post<null>('/auth/logout', { refreshToken: tokenStore.refresh })

export const getMe = () => get<UserInfo>('/auth/me')

export const changeOwnPassword = (oldPassword: string, newPassword: string) =>
  put<null>('/users/me/password', { oldPassword, newPassword })

/** 登录后拉取：嵌套导航树（DIR/MENU）+ 扁平权限编码（含 BUTTON） */
export const getMyPermissions = () => get<MyPermissions>('/permissions/my')
