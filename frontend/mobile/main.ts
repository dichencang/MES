import App from './App.uvue'

import { createSSRApp } from 'vue'
// uvx-ui 组件内部依赖 $uvx 全局工具对象，必须在入口注册插件
import uvxui from './uni_modules/uvx-ui/index.uts'

export function createApp() {
	const app = createSSRApp(App)
	app.use(uvxui)
	return {
		app
	}
}
