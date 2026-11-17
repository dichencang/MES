/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API 基地址，默认同源 /api/v1（开发期经 Vite 代理转发到后端 8080） */
  readonly VITE_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
