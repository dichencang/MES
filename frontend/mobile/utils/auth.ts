// 会话存储：令牌与权限快照。uni-app x 用 uni.getStorageSync / setStorageSync，不用 localStorage。
import { STORAGE_KEYS } from './config'
import type { AuthSession, MyPermissions, UserInfo } from '../types'

export const tokenStore = {
  get access(): string {
    return (uni.getStorageSync(STORAGE_KEYS.accessToken) as string) || ''
  },
  get refresh(): string {
    return (uni.getStorageSync(STORAGE_KEYS.refreshToken) as string) || ''
  },
  set(access: string, refresh: string): void {
    uni.setStorageSync(STORAGE_KEYS.accessToken, access)
    uni.setStorageSync(STORAGE_KEYS.refreshToken, refresh)
  },
  clear(): void {
    uni.removeStorageSync(STORAGE_KEYS.accessToken)
    uni.removeStorageSync(STORAGE_KEYS.refreshToken)
    uni.removeStorageSync(STORAGE_KEYS.permissions)
  },
}

/** 权限快照：刷新页面后无需重新拉取也能先渲染菜单（联网成功后覆盖） */
export const profileStore = {
  getUser(): UserInfo | null {
    return (uni.getStorageSync(STORAGE_KEYS.permissions) as UserInfo | null) ?? null
  },
  setUser(user: UserInfo): void {
    uni.setStorageSync(STORAGE_KEYS.permissions, user)
  },
  getPermissions(): MyPermissions | null {
    return (uni.getStorageSync('mes_permissions_full') as MyPermissions | null) ?? null
  },
  setPermissions(perm: MyPermissions): void {
    uni.setStorageSync('mes_permissions_full', perm)
  },
  clear(): void {
    uni.removeStorageSync(STORAGE_KEYS.permissions)
    uni.removeStorageSync('mes_permissions_full')
  },
}

export function rememberUsername(username: string, remember: boolean): void {
  if (remember) uni.setStorageSync(STORAGE_KEYS.username, username)
  else uni.removeStorageSync(STORAGE_KEYS.username)
}

export function getRememberedUsername(): string {
  return (uni.getStorageSync(STORAGE_KEYS.username) as string) || ''
}
