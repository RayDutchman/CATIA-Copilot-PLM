/**
 * account-management 主视图（ES Module 版）
 * 原：app/account-management/js/app.js
 */
import Backbone from 'backbone'
import Mustache from 'mustache'
import template from '../../../app/account-management/js/templates/content.html?raw'
import EditAccountView from './views/edit-account.js'

const AppView = Backbone.View.extend({
  el: '#content',

  events: {},

  initialize: function () {},

  render: function () {
    this.$el.html(Mustache.render(template, {
      i18n: window.App.config.i18n
    })).show()
    return this
  },

  editAccount: function () {
    var view = new EditAccountView()
    this.$('#account-management-content').html(view.renderAuthView().el)
  }
})

export default AppView
