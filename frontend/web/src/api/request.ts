// axios 请求层：统一响应包裹、Bearer token、访问令牌过期静默刷新（并发合并）、错误码处理。
// 依据契约 v1.0 §一/§二/§六：code=0 成功；2001 静默刷新后重放；2002/2003 清会话跳登录。
import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResult } from '@/types'

const BASE = import.meta.env.VITE_API_BASE || '/api/v1'

// 令牌存储（localStorage）。刷新时从这里读写，避免与 pinia 循环依赖。
const TOKEN_KEY = 'mes_access_token'
const REFRESH_KEY = 'mes_refresh_token'
export const tokenStore = {
  get access() { return localStorage.getItem(TOKEN_KEY) ?? '' },
  get refresh() { return localStorage.getItem(REFRESH_KEY) ?? '' },
  set(access: string, refresh: string) {
    localStorage.setItem(TOKEN_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_KEY) },
}

const http: AxiosInstance = axios.create({
  baseURL: BASE,
  timeout: 15000,
})

http.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  if (tokenStore.access) cfg.headers.set('Authorization', `Bearer ${tokenStore.access}`)
  return cfg
})

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

function onRefreshFailed() {
  tokenStore.clear()
  // 用事件通知应用层跳登录；避免 api 层直接依赖 router
  window.dispatchEvent(new CustomEvent('mes:unauthorized'))
}

/** 并发 401 只发一次刷新，其余请求挂起等待，成功后各自重放 */
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

http.interceptors.response.use(
  (resp) => {
    const body = resp.data as ApiResult<unknown>
    if (body && typeof body === 'object' && 'code' in body && body.code !== 0) {
      ElMessage.error(body.message || '操作失败')
      return Promise.reject(new Error(body.message))
    }
    return resp
  },
  async (err: AxiosError<ApiResult<unknown>>) => {
    const cfg = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const status = err.response?.status
    const code = err.response?.data?.code
    const message = err.response?.data?.message

    if (status === 401 && code === 2001 && cfg && !cfg._retry) {
      cfg._retry = true
      try {
        const token = await refreshOnce()
        cfg.headers.set('Authorization', `Bearer ${token}`)
        return http.request(cfg)
      } catch {
        onRefreshFailed()
        return Promise.reject(err)
      }
    }
    if (status === 401 && (code === 2002 || code === 2003)) {
      onRefreshFailed()
      return Promise.reject(err)
    }
    ElMessage.error(message || '请求失败')
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
