// 请求层：uni.request 封装（不依赖 axios，蒸汽模式兼容性更稳）。
// 错误码分流与 Web 端一致：2001 换新令牌重放一次（并发单飞）；2002/2003 清会话跳登录；其余统一提示。
import { BIZ_CODE, LOCAL_CODE } from '../constants/biz'
import { API_BASE } from './config'
import { tokenStore } from './auth'
import type { ApiResult } from '../types'

export class ApiError extends Error {
  code: number
  httpStatus: number

  constructor(code: number, message: string, httpStatus: number = 0) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

interface RequestResult<T> {
  status: number
  body: ApiResult<T> | null
}

/** Promise 包装 uni.request（用回调式，避免依赖 uni-app x 对 Promise 风格的差异） */
function rawRequest<T>(url: string, method: string, data: any, auth: boolean): Promise<RequestResult<T>> {
  return new Promise((resolve, reject) => {
    const header: Record<string, string> = { 'Content-Type': 'application/json' }
    if (auth && tokenStore.access) {
      header['Authorization'] = 'Bearer ' + tokenStore.access
    }

    uni.request({
      url: API_BASE + url,
      method: method as any,
      data: data,
      header: header,
      success: (res: any) => {
        const body = typeof res.data === 'string' ? null : (res.data as ApiResult<T>)
        resolve({ status: res.statusCode as number, body: body })
      },
      fail: (err: any) => reject(err),
    })
  })
}

// ── 令牌刷新：并发单飞 ─────────────────────────────────────
let refreshing = false
let waiters: Array<{ resolve: (token: string) => void; reject: (error: any) => void }> = []

async function refreshOnce(): Promise<string> {
  if (refreshing) {
    return new Promise<string>((resolve, reject) => {
      waiters.push({ resolve: resolve, reject: reject })
    })
  }

  refreshing = true
  try {
    const res = await rawRequest<{ accessToken: string; refreshToken: string }>(
      '/auth/refresh',
      'POST',
      { refreshToken: tokenStore.refresh },
      false,
    )
    if (res.status !== 200 || !res.body || res.body.code !== BIZ_CODE.OK) {
      throw new ApiError(res.body ? res.body.code : LOCAL_CODE.NETWORK, '刷新登录状态失败', res.status)
    }
    const session = res.body.data
    tokenStore.set(session.accessToken, session.refreshToken)
    for (const w of waiters) w.resolve(session.accessToken)
    return session.accessToken
  } catch (error) {
    for (const w of waiters) w.reject(error)
    throw error
  } finally {
    waiters = []
    refreshing = false
  }
}

function expireSession(): void {
  tokenStore.clear()
  uni.reLaunch({ url: '/pages/login/index' })
}

function toast(message: string): void {
  uni.showToast({ title: message, icon: 'none', duration: 2500 })
}

/** 统一请求入口。retry 为内部重放标记，sentToken 用于判断"期间是否已被别的请求刷新" */
async function api<T>(
  url: string,
  method: string = 'GET',
  data?: any,
  auth: boolean = true,
  retry: boolean = false,
  sentToken: string = '',
): Promise<T> {
  const tokenAtSend = sentToken || tokenStore.access

  let res: RequestResult<T>
  try {
    res = await rawRequest<T>(url, method, data, auth)
  } catch (error) {
    const err = new ApiError(LOCAL_CODE.NETWORK, '网络异常，请检查网络后重试')
    toast(err.message)
    throw err
  }

  const code = res.body ? res.body.code : undefined
  const message = res.body ? res.body.message : ''

  if (res.status === 200 && code === BIZ_CODE.OK && res.body) {
    return res.body.data
  }

  // 2001：令牌过期或已被刷新轮换 —— 换新令牌重放一次
  if (res.status === 401 && code === BIZ_CODE.TOKEN_EXPIRED && !retry) {
    try {
      // 若期间令牌已被其他请求刷新，直接用当前令牌重放，不再拿已轮换的 refreshToken 二次刷新
      if (auth && tokenAtSend && tokenStore.access && tokenAtSend !== tokenStore.access) {
        // tokenStore 已是新令牌，直接重放
      } else {
        await refreshOnce()
      }
      return await api<T>(url, method, data, auth, true, tokenAtSend)
    } catch (error) {
      expireSession()
      throw new ApiError(BIZ_CODE.SESSION_INVALID, '登录已失效，请重新登录', 401)
    }
  }

  // 2002 永久失效 / 2003 刷新令牌无效
  if (res.status === 401 && (code === BIZ_CODE.SESSION_INVALID || code === BIZ_CODE.REFRESH_INVALID)) {
    expireSession()
    const err = new ApiError(code as number, message || '登录已失效，请重新登录', res.status)
    toast(err.message)
    throw err
  }

  const err = new ApiError(code === undefined ? LOCAL_CODE.NETWORK : code, message || '请求失败', res.status)
  toast(err.message)
  throw err
}

export const get = <T>(url: string, data?: any, auth: boolean = true) => api<T>(url, 'GET', data, auth)
export const post = <T>(url: string, data?: any, auth: boolean = true) => api<T>(url, 'POST', data, auth)
export const put = <T>(url: string, data?: any, auth: boolean = true) => api<T>(url, 'PUT', data, auth)
export const del = <T>(url: string, data?: any, auth: boolean = true) => api<T>(url, 'DELETE', data, auth)
