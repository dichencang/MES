// 认证状态：用户信息、权限编码集合、动态菜单树。hasPerm 只查 permissionCodes。
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMyPermissions, getMe, login as loginReq, logout as logoutReq } from '@/api'
import { tokenStore } from '@/api/request'
import { useDictStore } from '@/stores/dict'
import { useTabsStore } from '@/stores/tabs'
import type { LoginPayload, PermNode, UserInfo } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const permissionCodes = ref<string[]>([])
  const navTree = ref<PermNode[]>([])
  const loaded = ref(false)

  const isSuper = computed(() => user.value?.isSuper === true)
  const codeSet = computed(() => new Set(permissionCodes.value))

  /** 权限判断：超管恒真，否则查 permissionCodes */
  const hasPerm = (code: string): boolean => isSuper.value || codeSet.value.has(code)

  function reset() {
    user.value = null
    permissionCodes.value = []
    navTree.value = []
    loaded.value = false
    tokenStore.clear()
    // 切账号后不能残留上一个账号的字典与页签
    useDictStore().clear()
    useTabsStore().clear()
  }

  async function login(payload: LoginPayload) {
    const session = await loginReq(payload)
    tokenStore.set(session.accessToken, session.refreshToken)
    await loadProfile()
  }

  /** 拉取用户信息 + 权限树，刷新页面后重建状态 */
  async function loadProfile() {
    const mePromise = getMe()
    const permPromise = getMyPermissions()
    const me = await mePromise
    const perm = await permPromise
    user.value = me
    permissionCodes.value = perm.permissionCodes
    navTree.value = perm.tree
    loaded.value = true
  }

  async function logout() {
    try { await logoutReq() } catch { /* 忽略登出接口失败，本地必清 */ }
    reset()
  }

  return { user, permissionCodes, navTree, loaded, isSuper, hasPerm, login, logout, loadProfile, reset }
})
