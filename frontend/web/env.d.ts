/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API 基地址，默认同源 /api/v1（开发期经 Vite 代理转发到后端 8080） */
  readonly VITE_API_BASE?: string
  /** 系统标题，显示在登录页、侧栏与浏览器标题 */
  readonly VITE_APP_TITLE?: string
  /** 环境标识：development / production */
  readonly VITE_APP_ENV?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
