// axios 请求层：统一响应包裹、Bearer 令牌、错误码分流、访问令牌静默刷新（并发单飞）。
// 依据「登录图片验证码增量契约」：
//   2001 令牌过期或旧令牌已被刷新轮换 → 换新令牌重放一次（并发共用同一刷新）
//   2002 永久失效 / 2003 刷新令牌无效     → 清会话跳登录
//   其余业务码（1001/2004/2005/9002/9003…）→ 统一弹后端 message 并抛出 ApiError
// 页面按 ApiError.code 决定表单行为，不再各自弹提示（避免一条错误弹两次）。
import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResult } from '@/types'
import { EVENT_UNAUTHORIZED, STORAGE_KEYS } from '@/constants'
import { BIZ_CODE, LOCAL_CODE } from '@/constants/biz'

const BASE = import.meta.env.VITE_API_BASE || '/api/v1'

/** 统一业务错误：页面拿 code 分流，拿 message 展示 */
export class ApiError extends Error {
  code: number
  httpStatus?: number
  data?: unknown

  constructor(code: number, message: string, httpStatus?: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.httpStatus = httpStatus
    this.data = data
  }
}

/** 令牌存储（localStorage）。刷新时直接读写，避免与 pinia 循环依赖。 */
export const tokenStore = {
  get access() { return localStorage.getItem(STORAGE_KEYS.accessToken) ?? '' },
  get refresh() { return localStorage.getItem(STORAGE_KEYS.refreshToken) ?? '' },
  set(access: string, refresh: string) {
    localStorage.setItem(STORAGE_KEYS.accessToken, access)
    localStorage.setItem(STORAGE_KEYS.refreshToken, refresh)
  },
  clear() {
    localStorage.removeItem(STORAGE_KEYS.accessToken)
    localStorage.removeItem(STORAGE_KEYS.refreshToken)
  },
}

const http: AxiosInstance = axios.create({
  baseURL: BASE,
  timeout: 15000,
})

http.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  if (tokenStore.access) cfg.headers.set('Authorization', `Bearer ${tokenStore.access}`)
  return cfg
})

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean }
type Pending = { resolve: (t: string) => void; reject: (e: unknown) => void }
let refreshing = false
let waiters: Pending[] = []

async function doRefresh(): Promise<string> {
  const res = await axios.post<ApiResult<{ accessToken: string; refreshToken: string }>>(
    `${BASE}/auth/refresh`,
    { refreshToken: tokenStore.refresh },
  )
  const session = res.data.data
  tokenStore.set(session.accessToken, session.refreshToken)
  return session.accessToken
}

/** 并发 401 只发一次刷新，其余请求挂起等待，成功后各自用新令牌重放 */
async function refreshOnce(): Promise<string> {
  if (refreshing) {
    return new Promise<string>((resolve, reject) => waiters.push({ resolve, reject }))
  }
  refreshing = true
  try {
    const token = await doRefresh()
    waiters.forEach((w) => w.resolve(token))
    return token
  } catch (e) {
    waiters.forEach((w) => w.reject(e))
    throw e
  } finally {
    waiters = []
    refreshing = false
  }
}

/**
 * 取一个"可用于重放"的令牌。
 * 关键：若该请求发出后令牌已被别的请求刷新过（请求头里的令牌 ≠ 当前令牌），
 * 直接用当前令牌重放即可，**不能再拿已轮换的 refreshToken 去刷**（会拿到 2003 被误踢）。
 */
async function ensureFreshToken(cfg: InternalAxiosRequestConfig): Promise<string> {
  const raw = cfg.headers.get('Authorization')
  const sent = typeof raw === 'string' ? raw : ''
  const current = tokenStore.access
  if (sent && current && sent !== `Bearer ${current}`) return current
  return refreshOnce()
}

function expireSession() {
  tokenStore.clear()
  // 用事件通知应用层跳登录；避免 api 层直接依赖 router
  window.dispatchEvent(new CustomEvent(EVENT_UNAUTHORIZED))
}

http.interceptors.response.use(
  (resp) => {
    const body = resp.data as ApiResult<unknown>
    // 防御：后端约定失败走非 2xx，此处兜住"200 + code≠0"的意外实现
    if (body && typeof body === 'object' && 'code' in body && body.code !== BIZ_CODE.OK) {
      const err = new ApiError(body.code, body.message || '操作失败', resp.status, body.data)
      ElMessage.error(err.message)
      return Promise.reject(err)
    }
    return resp
  },
  async (error: AxiosError<ApiResult<unknown>>) => {
    const cfg = error.config as RetryConfig | undefined
    const status = error.response?.status
    const body = error.response?.data
    const code = body?.code
    const bizMessage = body?.message

    // 网络层错误（无响应）
    if (!error.response) {
      const timeout = error.code === 'ECONNABORTED'
      const err = new ApiError(
        timeout ? LOCAL_CODE.TIMEOUT : LOCAL_CODE.NETWORK,
        timeout ? '请求超时，请重试' : '网络异常，请检查网络后重试',
      )
      ElMessage.error(err.message)
      return Promise.reject(err)
    }

    // 2001：令牌过期或已被轮换 —— 换新令牌重放一次
    if (status === 401 && code === BIZ_CODE.TOKEN_EXPIRED) {
      if (cfg && !cfg._retry) {
        cfg._retry = true
        try {
          const token = await ensureFreshToken(cfg)
          cfg.headers.set('Authorization', `Bearer ${token}`)
          return http.request(cfg)
        } catch {
          expireSession()
          return Promise.reject(new ApiError(BIZ_CODE.SESSION_INVALID, '登录已失效，请重新登录', status))
        }
      }
      // 重放后仍 2001：令牌确实不可用
      expireSession()
      return Promise.reject(new ApiError(BIZ_CODE.TOKEN_EXPIRED, bizMessage || '登录已失效，请重新登录', status))
    }

    // 2002 永久失效 / 2003 刷新令牌无效 —— 清会话
    if (status === 401 && (code === BIZ_CODE.SESSION_INVALID || code === BIZ_CODE.REFRESH_INVALID)) {
      expireSession()
      return Promise.reject(new ApiError(code, bizMessage || '登录已失效，请重新登录', status))
    }

    // 其余业务错误：统一提示，页面按 code 处理表单
    const err = new ApiError(code ?? LOCAL_CODE.NETWORK, bizMessage || '请求失败', status, body?.data)
    ElMessage.error(err.message)
    return Promise.reject(err)
  },
)

/** 统一取 data：GET/写入都只关心 data 部分 */
export async function api<T>(config: AxiosRequestConfig): Promise<T> {
  const resp = await http.request<ApiResult<T>>(config)
  return resp.data.data
}

export const get = <T>(url: string, params?: Record<string, unknown>) => api<T>({ method: 'GET', url, params })
export const post = <T>(url: string, data?: unknown) => api<T>({ method: 'POST', url, data })
export const put = <T>(url: string, data?: unknown) => api<T>({ method: 'PUT', url, data })
export const del = <T>(url: string) => api<T>({ method: 'DELETE', url })

export default http
