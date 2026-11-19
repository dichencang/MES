// 后端地址。
// - Android 模拟器：10.0.2.2 是模拟器访问宿主机的固定地址（当前值）
// - 真机：改成电脑在局域网的 IP，如 http://192.168.1.8:8080，手机与电脑同一 WiFi
// - 后端固定 8080，CORS 为 ["*"]，无需额外白名单
export const API_BASE = 'http://10.0.2.2:8080'

/** 本地存储键，与 Web 端一致 */
export const STORAGE_KEYS = {
  accessToken: 'mes_access_token',
  refreshToken: 'mes_refresh_token',
  username: 'mes_login_username',
  permissions: 'mes_permissions',
} as const
