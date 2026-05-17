/**
 * vue-i18n 实例
 * 合并 localization/ 下已生成的翻译对象，供所有 Vue 模块复用
 */
import { createI18n } from 'vue-i18n'
import commonStrings from '../localization/common.js'

// 按需加载各模块翻译，调用方通过 mergeLocaleMessage 追加
const i18n = createI18n({
  legacy: false,                                      // 使用 Composition API 模式（useI18n）
  locale: localStorage.getItem('locale') || 'en',
  fallbackLocale: 'en',
  messages: {
    en: commonStrings.en || {},
    fr: commonStrings.fr || {},
    zh: commonStrings.zh || {},
    ru: commonStrings.ru || {},
  },
  // 缺失 key 时返回空字符串，与原版 Mustache {{i18n.KEY}} 遇 undefined 静默的行为一致
  // 避免将 key 名直接显示到页面上
  missing: (_locale, _key) => '',
  missingWarn: false,
  fallbackWarn: false,
})

/**
 * 向 i18n 实例追加模块级翻译
 * @param {Object} moduleStrings  格式同 localization/*.js 的默认导出：{ en:{}, fr:{}, zh:{}, ru:{} }
 */
export function mergeModuleStrings(moduleStrings) {
  const locales = ['en', 'fr', 'zh', 'ru']
  locales.forEach((locale) => {
    if (moduleStrings[locale]) {
      i18n.global.mergeLocaleMessage(locale, moduleStrings[locale])
    }
  })
}

export default i18n
