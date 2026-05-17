/**
 * account-management 路由（ES Module 版）
 * 原：app/account-management/js/router.js
 */
import Backbone from 'backbone'
import singletonDecorator from '../../common-objects/common/singleton_decorator.js'

const Router = Backbone.Router.extend({
  routes: {
    '': 'editAccount'
  },

  editAccount: function () {
    window.App.appView.render()
    window.App.headerView.render()
    window.App.appView.editAccount()
  }
})

export default singletonDecorator(Router)
