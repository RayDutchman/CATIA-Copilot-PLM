/**
 * Pinia store：应用配置（对应原 window.App.config 的服务器属性部分）
 * 封装 resolveServerProperties 逻辑，替代 contextResolver.js 中的同名方法
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

function addTrailingSlash(s) {
  if (!s) return '/'
  return s.endsWith('/') ? s : s + '/'
}

export const useAppStore = defineStore('app', () => {
  const apiEndPoint       = ref('')
  const contextPath       = ref('')
  const webSocketEndPoint = ref('')
  const serverBasePath    = ref('')
  const preferLoginWith   = ref(false)
  const providers         = ref([])
  const ready             = ref(false)   // resolveServerProperties 完成后置 true

  /**
   * 从 webapp.properties.json 加载服务器配置
   * @param {string} relativeLocation  相对于当前页面的路径前缀，默认 '..'
   */
  async function resolveServerProperties(relativeLocation = '..') {
    const res = await fetch(`${relativeLocation}/webapp.properties.json?__BUST_CACHE__`)
    if (!res.ok) throw new Error('Failed to load webapp.properties.json')
    const properties = await res.json()

    const isSSL = properties.server.ssl
    const base  = '://' + properties.server.domain + ':' + properties.server.port +
                  addTrailingSlash(properties.server.contextPath)
    const wsBase = properties.server.wsDomain
      ? '://' + properties.server.wsDomain + ':' + properties.server.port +
        addTrailingSlash(properties.server.contextPath)
      : base

    serverBasePath.value    = (isSSL ? 'https' : 'http') + base
    apiEndPoint.value       = (isSSL ? 'https' : 'http') + base + 'api'
    webSocketEndPoint.value = (isSSL ? 'wss'   : 'ws')   + wsBase + 'ws'
    contextPath.value       = addTrailingSlash(properties.contextPath || '')
    preferLoginWith.value   = !!properties.preferLoginWith
    ready.value             = true
  }

  return {
    apiEndPoint, contextPath, webSocketEndPoint,
    serverBasePath, preferLoginWith, providers, ready,
    resolveServerProperties,
  }
})
