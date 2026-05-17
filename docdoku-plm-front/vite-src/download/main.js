/**
 * download 模块入口（ES Module 版）
 *
 * 原 AMD 流程：require.config → require(['contextResolver','i18n!...'], fn)
 * 迁移后：直接 import，async/await 读取服务器配置，然后渲染视图
 */
import $ from 'jquery'
import _ from 'underscore'
import Backbone from 'backbone'

// 导入 download 模块样式（Vite 会处理 Less 并注入 CSS）
import '../../app/less/download/style.less'

import AppView from './js/app.js'
import downloadStrings from '../localization/download.js'

// ── 全局 App 对象（Backbone 视图通过 window.App 读取配置） ──
window.App = window.App || {}

// 根据 localStorage 或浏览器语言决定 locale
const SUPPORTED = ['fr', 'ru', 'zh']
function detectLocale() {
  try {
    const stored = window.localStorage.locale
    if (stored) return stored
    const nav = (navigator.language || '').split('-')[0].toLowerCase()
    return SUPPORTED.includes(nav) ? nav : 'en'
  } catch {
    return 'en'
  }
}

const locale = detectLocale()

window.App.config = {
  contextPath: '/',
  apiEndPoint: '',
  locale,
  // 合并当前语言字符串，英文作为 fallback
  i18n: Object.assign({}, downloadStrings.en, downloadStrings[locale] || {}),
}

/**
 * 从 webapp.properties.json 读取服务器配置
 * 失败时静默降级（本地开发时可能不可用）
 */
async function resolveServerProperties() {
  try {
    const res = await fetch('../webapp.properties.json')
    if (!res.ok) return
    const props = await res.json()
    const isSSL = props.server && props.server.ssl
    const base =
      (isSSL ? 'https' : 'http') +
      '://' +
      props.server.domain +
      ':' +
      props.server.port +
      (props.server.contextPath || '/')
    window.App.config.apiEndPoint = base + 'api'
    window.App.config.contextPath = (props.contextPath || '/').replace(/\/?$/, '/')
  } catch {
    // 开发环境可能无法访问 properties，忽略
  }
}

// 启动：先读配置，再渲染视图
resolveServerProperties().finally(() => {
  const appView = new AppView()
  appView.render()
})
