// 页签状态：记录已打开的菜单页，退出登录或会话失效时清空。
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface TabItem {
  path: string
  title: string
  /** 固定标签（如首页），不可关闭 */
  affix?: boolean
}

export const useTabsStore = defineStore('tabs', () => {
  const tabs = ref<TabItem[]>([])

  function add(tab: TabItem) {
    if (!tab.path || tab.path === '/login' || tab.path.startsWith('/error')) return
    if (tabs.value.some((t) => t.path === tab.path)) return
    tabs.value.push(tab)
  }

  function remove(path: string) {
    tabs.value = tabs.value.filter((t) => t.path !== path || t.affix)
  }

  function clear() {
    tabs.value = []
  }

  return { tabs, add, remove, clear }
})
