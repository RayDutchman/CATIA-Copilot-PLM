/**
 * Pinia store：账户与认证状态
 * 封装 resolveAccount / resolveWorkspaces / logout 逻辑
 * 替代 contextResolver.js 中的同名方法
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAppStore } from './app.js'

export const useAuthStore = defineStore('auth', () => {
  const account    = ref(null)
  const workspaces = ref({ administratedWorkspaces: [], nonAdministratedWorkspaces: [], allWorkspaces: [] })
  const isLoggedIn = ref(!!localStorage.jwt)

  const userName = computed(() => account.value?.name  || '')
  const login    = computed(() => account.value?.login || '')
  const isAdmin  = computed(() => !!account.value?.admin)

  /**
   * 加载当前登录账户信息
   * 若 locale 与账户语言不一致则自动 reload（与原 contextResolver 行为一致）
   */
  async function resolveAccount() {
    const appStore = useAppStore()
    const res = await fetch(appStore.apiEndPoint + '/accounts/me', {
      headers: { Authorization: 'Bearer ' + localStorage.jwt },
    })
    if (res.status === 401) {
      delete localStorage.jwt
      window.location.href = appStore.contextPath + 'index.html?denied=true&originURL=' +
        encodeURIComponent(window.location.pathname + window.location.hash)
      throw new Error('Unauthorized')
    }
    if (!res.ok) throw new Error('Failed to load account')

    const data = await res.json()
    account.value  = data
    isLoggedIn.value = true

    // 同步 locale —— 与原版逻辑完全一致
    const accountLocale = data.language || 'en'
    if (localStorage.locale !== accountLocale) {
      localStorage.locale = accountLocale
      window.location.reload()
    }

    // 更新响应头中的新 JWT（如果有）
    const newJwt = res.headers.get('jwt')
    if (newJwt && newJwt !== localStorage.jwt) {
      localStorage.jwt = newJwt
    }

    return data
  }

  /** 加载用户的工作区列表 */
  async function resolveWorkspaces() {
    const appStore = useAppStore()
    const res = await fetch(appStore.apiEndPoint + '/workspaces', {
      headers: { Authorization: 'Bearer ' + localStorage.jwt },
    })
    if (!res.ok) return
    const data = await res.json()

    const adminIds = new Set((data.administratedWorkspaces || []).map(w => w.id))
    workspaces.value = {
      administratedWorkspaces:    data.administratedWorkspaces    || [],
      allWorkspaces:              data.allWorkspaces              || [],
      nonAdministratedWorkspaces: (data.allWorkspaces || []).filter(w => !adminIds.has(w.id)),
    }
    return workspaces.value
  }

  /** 登出：清除 JWT，调用后端 logout 接口，跳转登录页 */
  async function logout() {
    const appStore = useAppStore()
    delete localStorage.jwt
    isLoggedIn.value = false
    try {
      await fetch(appStore.apiEndPoint + '/auth/logout', {
        headers: { Authorization: 'Bearer ' + localStorage.jwt }
      })
    } catch (_) { /* 忽略网络错误 */ }
    window.location.href = appStore.contextPath + 'index.html?logout=true'
  }

  return {
    account, workspaces, isLoggedIn, userName, login, isAdmin,
    resolveAccount, resolveWorkspaces, logout,
  }
})
