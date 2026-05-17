/**
 * useApi —— 带 JWT 自动注入的 fetch 封装
 * 替代 contextResolver.js 中的 XHR 拦截逻辑
 *
 * 用法：
 *   const { get, put, post } = useApi()
 *   const account = await get('/accounts/me')
 */
import { useAppStore } from '../store/app.js'

export function useApi() {
  const appStore = useAppStore()

  /**
   * 底层 fetch，自动注入 JWT、处理 401、刷新响应头中的新 token
   */
  async function apiFetch(path, options = {}) {
    const url = path.startsWith('http') ? path : appStore.apiEndPoint + path

    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    }
    if (localStorage.jwt) {
      headers['Authorization'] = 'Bearer ' + localStorage.jwt
    }

    const res = await fetch(url, { ...options, headers })

    // 更新响应头中的新 JWT
    const newJwt = res.headers.get('jwt')
    if (newJwt && newJwt !== localStorage.jwt) {
      localStorage.jwt = newJwt
    }

    // 401：清除 token，跳转登录页
    if (res.status === 401) {
      delete localStorage.jwt
      window.location.href = appStore.contextPath + 'index.html?denied=true&originURL=' +
        encodeURIComponent(window.location.pathname + window.location.hash)
      throw new Error('Unauthorized')
    }

    return res
  }

  /** GET 并解析 JSON */
  async function get(path) {
    const res = await apiFetch(path)
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
    return res.json()
  }

  /** PUT with JSON body */
  async function put(path, body) {
    const res = await apiFetch(path, { method: 'PUT', body: JSON.stringify(body) })
    if (!res.ok) throw new Error(await res.text())
    return res.json().catch(() => null)
  }

  /** POST with JSON body */
  async function post(path, body) {
    const res = await apiFetch(path, { method: 'POST', body: JSON.stringify(body) })
    if (!res.ok) throw new Error(await res.text())
    return res.json().catch(() => null)
  }

  /** DELETE */
  async function del(path) {
    const res = await apiFetch(path, { method: 'DELETE' })
    if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`)
    return res.status !== 204 ? res.json().catch(() => null) : null
  }

  return { apiFetch, get, put, post, del }
}
