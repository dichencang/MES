// v-perm 按钮权限指令：无权限则从 DOM 移除（不渲染，不是置灰）。依据契约 v1.0 §三。
import type { Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

const apply = (el: HTMLElement, code: string) => {
  const auth = useAuthStore()
  if (!auth.hasPerm(code)) {
    el.dataset.permDenied = code
    el.style.display = 'none'
  } else if (el.dataset.permDenied) {
    delete el.dataset.permDenied
    el.style.display = ''
  }
}

export const permDirective: Directive<HTMLElement, string> = {
  mounted(el, binding) { apply(el, binding.value) },
  updated(el, binding) { if (binding.value !== binding.oldValue) apply(el, binding.value) },
}
