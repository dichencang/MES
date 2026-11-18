/// <reference types="vite/client" />

// 由 vite.config.ts 的 define 注入，值为启动参数 VITE_API_BASE_URL；未注入时为空串。
declare const __API_BASE_URL__: string;

declare module '*.vue' {
  import { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}
