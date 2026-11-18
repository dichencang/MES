import { defineConfig, loadEnv } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

// 后端 API 基地址由启动参数/环境变量注入，移动端不固定端口。
// 用法：VITE_API_BASE_URL=http://192.168.1.10:8080 npm run dev:h5
// 未注入时按当前 H5 访问_host 的 8080 端口推导（见 src/utils/api.ts）。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  return {
    define: {
      __API_BASE_URL__: JSON.stringify(env.VITE_API_BASE_URL || ""),
    },
    // 显式绑 IPv4 全部网卡：既避开 Web 端固定的 5173，又便于手机浏览器/真机同局域网访问。
    server: {
      host: "0.0.0.0",
      port: 5174,
    },
    plugins: [uni()],
  };
});
