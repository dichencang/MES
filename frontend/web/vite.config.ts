import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  // 不挂 vite-plugin-vue-devtools：它会在页面左下角注入浮标，浏览器走查时易误点弹出大面板遮挡页面。
  // 需要调试时用浏览器原生开发者工具，不再注入该浮标。
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // 端口硬约束（见 PROJECT_CONTEXT §5）：5173 且不允许漂移，后端 CORS 白名单依赖它
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // 后端固定 0.0.0.0:8080；前端请求统一带 /api/v1 前缀（契约约定），代理剥掉该前缀后转发到后端路由。
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1/, ''),
      },
    },
  },
  build: {
    // 分包：把 UI 库与框架拆出去，避免单个 chunk 过大影响首屏
    rollupOptions: {
      output: {
        manualChunks(id: string): string | undefined {
          if (!id.includes('node_modules')) return undefined
          const p = id.replace(/\\/g, '/')
          if (p.includes('/element-plus/')) return 'element-plus'
          if (p.includes('/@element-plus/icons-vue/')) return 'ep-icons'
          if (p.includes('/vue-router/') || p.includes('/pinia/')) return 'vue-vendor'
          return undefined
        },
      },
    },
    // Element Plus 全量引入（模板依赖 el-* 与动态图标 <component :is="iconName">），
    // gzip 后约 358 kB；内网系统一次加载后走缓存，暂不做按需引入，故放宽告警阈值。
    chunkSizeWarningLimit: 1200,
  },
})
