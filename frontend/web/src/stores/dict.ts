// 字典缓存：业务下拉（物料单位、不良类型、工单状态…）在会话内只取一次。
// GET /dict-data/{dictCode} 仅校验会话，业务角色无需系统管理权限；退出登录时 clear()。
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dictOptions } from '@/api'
import type { DictOption } from '@/types'

export const useDictStore = defineStore('dict', () => {
  const cache = ref<Record<string, DictOption[]>>({})
  // 同一字典并发请求只发一次（多组件同时挂载时常见）
  const pending = new Map<string, Promise<DictOption[]>>()

  async function load(code: string, force = false): Promise<DictOption[]> {
    const cached = cache.value[code]
    if (!force && cached) return cached
    const running = pending.get(code)
    if (running) return running

    const task = dictOptions(code)
      .then((list) => {
        cache.value[code] = list
        return list
      })
      .finally(() => pending.delete(code))

    pending.set(code, task)
    return task
  }

  /** 同步读已缓存的选项（未加载时为空数组，不触发请求） */
  function options(code: string): DictOption[] {
    return cache.value[code] ?? []
  }

  /** 值转显示名，找不到时原样返回值 */
  function label(code: string, value: string): string {
    return options(code).find((i) => i.dictValue === value)?.dictLabel ?? value
  }

  function clear() {
    cache.value = {}
    pending.clear()
  }

  return { cache, load, options, label, clear }
})
