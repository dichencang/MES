/**
 * 后端 API 基地址解析。
 *
 * 移动端不固定端口，基地址按以下优先级确定：
 * 1. 启动参数/环境变量 VITE_API_BASE_URL（如手机真机调试时指向局域网 PC 的 8080）
 * 2. H5 下按当前访问 host 推导同机 8080（本机开发：访问 5173 → 请求 8080）
 * 3. App 下无 window 时退回 http://127.0.0.1:8080（仅占位，实际必须显式注入）
 *
 * 用法：npm run dev:h5 或 VITE_API_BASE_URL=http://192.168.1.10:8080 npm run dev:h5
 */
function resolveBaseUrl(): string {
  const injected = typeof __API_BASE_URL__ !== "undefined" ? __API_BASE_URL__ : "";
  if (injected) return injected.replace(/\/+$/, "");

  // #ifdef H5
  const host = window.location.hostname;
  return `${window.location.protocol}//${host}:8080/api/v1`;
  // #endif

  // #ifndef H5
  return "http://127.0.0.1:8080/api/v1";
  // #endif
}

export const API_BASE_URL = resolveBaseUrl();
