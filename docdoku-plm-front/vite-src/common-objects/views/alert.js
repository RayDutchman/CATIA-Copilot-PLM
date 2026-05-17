/**
 * Alert 视图（ES Module 版）
 * 原：app/js/common-objects/views/alert.js
 * 模板内联为字符串，替代 text! 插件
 */
import Backbone from 'backbone'
import Mustache from 'mustache'

// 内联模板（原 app/js/common-objects/templates/alert.html）
import template from '../../../app/js/common-objects/templates/alert.html?raw'

const AlertView = Backbone.View.extend({
  event: {
    'click .close': 'onClose'
  },

  render: function () {
    this.$el.html(Mustache.render(template, {
      model: {
        type: this.options.type,
        title: this.options.title,
        message: this.options.message
      }
    }))
    return this
  },

  onClose: function () {
    this.remove()
  }
})

export default AlertView
