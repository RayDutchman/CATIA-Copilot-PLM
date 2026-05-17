/**
 * account-management 模块入口（ES Module 版）
 *
 * 原 AMD 流程：require.config → require(['contextResolver','i18n!...'], fn)
 *   → ContextResolver.resolveServerProperties('..')
 *   → .then(resolveAccount) → .then(resolveWorkspaces) → buildView()
 */
import _ from 'underscore'
import Backbone from 'backbone'

// 样式
import '../../app/less/account-management/style.less'

// common-objects（ES Module 版，位于 vite-src/common-objects/）
import ContextResolver from '../common-objects/contextResolver.js'

// i18n（ES Module 版，位于 vite-src/localization/）
import commonStrings from '../localization/common.js'
import accountStrings from '../localization/account-management.js'

// 根据 localStorage / 浏览器语言决定 locale
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

// 合并 i18n 字符串（通用 + 模块专用，模块专用覆盖同名 key）
window.App = window.App || {}
window.App.config = window.App.config || {}
window.App.config.i18n = Object.assign(
  {},
  commonStrings.en,
  commonStrings[locale] || {},
  accountStrings.en,
  accountStrings[locale] || {}
)

// ── 启动：解析服务器配置 → 解析账户 → 解析工作区 → 构建视图 ──
ContextResolver.resolveServerProperties('..')
  .then(() => ContextResolver.resolveAccount())
  .then(() => ContextResolver.resolveWorkspaces())
  .then(async () => {
    const [
      { default: AppView },
      { default: Router },
      { default: HeaderView },
    ] = await Promise.all([
      import('./js/app.js'),
      import('./js/router.js'),
      import('../common-objects/views/header.js'),
    ])

    window.App.appView = new AppView()
    window.App.headerView = new HeaderView()
    // CoWorkersView 在此模块中暂不使用，跳过 setCoWorkersView
    window.App.router = Router.getInstance()
    Backbone.history.start()
  })
