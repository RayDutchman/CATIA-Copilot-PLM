/**
 * Header 视图（ES Module 版）
 * 原：app/js/common-objects/views/header.js
 */
import $ from 'jquery'
import _ from 'underscore'
import Backbone from 'backbone'
import Mustache from 'mustache'
import template from '../../../app/js/common-objects/templates/header.html?raw'

const HeaderView = Backbone.View.extend({
  el: '#header',

  events: {
    'click #logout_link a': 'logout'
  },

  render: function () {
    var $el = this.$el
    var workspaces = window.App.config.workspaces

    function isCurrent(workspace) {
      workspace.isCurrent = workspace.id === window.App.config.workspaceId
    }

    if (workspaces) {
      _.each(workspaces.administratedWorkspaces, isCurrent)
      _.each(workspaces.nonAdministratedWorkspaces, isCurrent)
    }

    $el.html(Mustache.render(template, {
      connected: window.App.config.connected,
      currentWorkspace: window.App.config.workspaceId,
      contextPath: window.App.config.contextPath,
      administratedWorkspaces: workspaces ? workspaces.administratedWorkspaces : null,
      nonAdministratedWorkspaces: workspaces ? workspaces.nonAdministratedWorkspaces : null,
      i18n: window.App.config.i18n,
      userName: window.App.config.userName,
      isDocumentManagement: window.location.pathname.match('/document-management/'),
      isProductManagement: window.location.pathname.match('/product-management/'),
      isProductStructure: window.location.pathname.match('/product-structure/'),
      isChangeManagement: window.location.pathname.match('/change-management/'),
      isWorkspaceManagement: window.location.pathname.match('/workspace-management/'),
      isAdmin: window.App.config.admin
    }))

    $el.show().addClass('loaded')

    if (this.CoWorkersView) {
      var CoWorkersView = this.CoWorkersView
      new CoWorkersView().render()
    }

    return this
  },

  removeActionDisabled: function () {
    this.$('#coworkers_access_module_entries').find('.fa-globe').removeClass('corworker-action-disable').addClass('corworker-action')
  },

  addActionDisabled: function () {
    this.$('#coworkers_access_module_entries').find('.fa-globe').removeClass('corworker-action').addClass('corworker-action-disable')
  },

  setCoWorkersView: function (View) {
    this.CoWorkersView = View
  },

  logout: function () {
    delete localStorage.jwt
    $.get(window.App.config.apiEndPoint + '/auth/logout').complete(function () {
      window.location.href = window.App.config.contextPath + '?logout=true'
    })
  }
})

export default HeaderView
