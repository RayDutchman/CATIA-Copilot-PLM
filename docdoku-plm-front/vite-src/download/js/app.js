/**
 * download 模块主视图（ES Module 版）
 *
 * 原 AMD：define(['backbone','mustache','text!templates/content.html'], fn)
 * 迁移后：ES import，Mustache 模板用 ?raw 方式导入
 */
import Backbone from 'backbone'
import Mustache from 'mustache'

// Vite 的 ?raw 查询参数让模板以字符串形式导入，替代 requirejs-text 插件
import template from '../../../app/download/js/templates/content.html?raw'

const AppView = Backbone.View.extend({
  el: '#content',

  render() {
    // 用 Mustache 渲染模板并写入 DOM，与原版逻辑完全一致
    this.$el
      .html(
        Mustache.render(template, {
          i18n: window.App.config.i18n,
          contextPath: window.App.config.contextPath,
        })
      )
      .show()
    return this
  },
})

export default AppView
