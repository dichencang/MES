// 字典便捷用法：setup 中声明要用的字典编码，挂载时自动加载（已缓存则直接命中）。
//   const { options, label } = useDict('material_unit', 'work_order_status')
import { onMounted } from 'vue'
import { useDictStore } from '@/stores/dict'
import type { DictOption } from '@/types'

export function useDict(...codes: string[]) {
  const store = useDictStore()

  onMounted(() => {
    for (const code of codes) void store.load(code)
  })

  return {
    /** 下拉选项（响应式：加载完成后自动更新） */
    options: (code: string): DictOption[] => store.options(code),
    /** 值 → 中文名 */
    label: (code: string, value: string): string => store.label(code, value),
    /** 强制刷新某个字典 */
    reload: (code: string) => store.load(code, true),
  }
}
