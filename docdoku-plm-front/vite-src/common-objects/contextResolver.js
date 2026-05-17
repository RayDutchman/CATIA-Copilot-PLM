/**
 * ContextResolver（ES Module 版）
 * 原：app/js/common-objects/contextResolver.js
 *
 * 负责：
 * 1. 初始化 window.App.config
 * 2. 拦截 XHR 添加 JWT Bearer token
 * 3. 处理 401 自动重定向到登录页
 * 4. resolveServerProperties / resolveAccount / resolveWorkspaces 等异步方法
 */
import $ from 'jquery'
import _ from 'underscore'
import moment from 'moment'
import User from './models/user.js'
import Workspace from './models/workspace.js'
import Organization from './models/organization.js'
import jwtDecode from 'jwt-decode'
import Logger from './log.js'
import Backbone from 'backbone'

// ── 全局 App.config 初始化 ──
window.App = window.App || {}
window.App.config = Object.assign({
  login: '',
  groups: [],
  contextPath: '',
  apiEndPoint: '',
  webSocketEndPoint: '',
  providers: [],
  preferLoginWith: false,
  locale: window.localStorage.getItem('locale') || 'en'
}, window.App.config || {})

window.App.setDebug = function (state) {
  window.App.debug = state
  if (state) {
    document.body.classList.add('debug')
  } else {
    document.body.classList.remove('debug')
  }
}

// ── JWT 自动刷新 ──
var refreshTimer

var refreshFunction = function () {
  Logger.log('JWT', 'Keep alive token')
  $.ajax(window.App.config.apiEndPoint + '/accounts/me')
}

var scheduleTokenRefresh = function () {
  if (!refreshTimer) {
    var decoded = jwtDecode(localStorage.jwt)
    var expTimeStamp = decoded.exp * 1000
    var expiresIn = (expTimeStamp - Date.now())
    var fromNow = moment(expTimeStamp).fromNow()
    var timeout = expiresIn - 2 * 60 * 1000
    if (!refreshTimer && timeout > 0) {
      Logger.log('JWT', 'Expires ' + fromNow)
      Logger.log('JWT', 'Next token refresh scheduled ' + moment(Date.now() + timeout).fromNow())
      refreshTimer = setTimeout(refreshFunction, timeout)
    }
  }
}

var parseTokenFromResponse = function (xhr) {
  try {
    var jwt = xhr.getResponseHeader('jwt')
    if (jwt && jwt !== localStorage.jwt) {
      Logger.log('JWT', 'new token set')
      localStorage.jwt = jwt
      scheduleTokenRefresh()
    }
  } catch (e) {
    console.log(e)
  }
}

// ── XHR 拦截：自动注入 JWT Authorization 头 ──
;(function (send) {
  XMLHttpRequest.prototype.send = function (data) {
    if (localStorage.jwt) {
      this.setRequestHeader('Authorization', 'Bearer ' + localStorage.jwt)
    }
    send.call(this, data)
  }
})(XMLHttpRequest.prototype.send)

// ── XHR 拦截：处理 401 自动跳转 ──
;(function (open) {
  XMLHttpRequest.prototype.open = function () {
    this.addEventListener('readystatechange', function () {
      if (this.status === 401) {
        delete localStorage.jwt
        var isLoginPage = [window.App.config.contextPath + 'index.html', window.App.config.contextPath]
          .indexOf(window.location.pathname) > -1
        if (!isLoginPage) {
          window.location.href = window.App.config.contextPath + 'index.html?denied=true&originURL=' +
            encodeURIComponent(window.location.pathname + window.location.hash)
        }
        return
      }
      parseTokenFromResponse(this)
    }, false)
    open.apply(this, arguments)
  }
})(XMLHttpRequest.prototype.open)

// ── Backbone.Collection.fetch 添加 beforeFetch 事件 ──
;(function () {
  var fetch = Backbone.Collection.prototype.fetch
  Backbone.Collection.prototype.fetch = function () {
    this.trigger('beforeFetch')
    return fetch.apply(this, arguments)
  }
})()

// ── 工具函数 ──
function onError(res) {
  return res
}

function addTrailingSlash(s) {
  function endsWith(str, suffix) {
    return str.indexOf(suffix, str.length - suffix.length) !== -1
  }
  return s ? endsWith(s, '/') ? s : s + '/' : '/'
}

// ── ContextResolver 构造函数 ──
var ContextResolver = function () {}

ContextResolver.prototype.resolveServerProperties = function (relativeLocation) {
  return $.getJSON(relativeLocation + '/webapp.properties.json?__BUST_CACHE__').then(function (properties) {
    var isSSL = properties.server.ssl
    var base = '://' + properties.server.domain + ':' + properties.server.port + addTrailingSlash(properties.server.contextPath)
    var wsBase = properties.server.wsDomain
      ? '://' + properties.server.wsDomain + ':' + properties.server.port + addTrailingSlash(properties.server.contextPath)
      : base
    window.App.config.serverBasePath = (isSSL ? 'https' : 'http') + base
    window.App.config.apiEndPoint = (isSSL ? 'https' : 'http') + base + 'api'
    window.App.config.webSocketEndPoint = (isSSL ? 'wss' : 'ws') + wsBase + 'ws'
    window.App.config.contextPath = addTrailingSlash(properties.contextPath)
    window.App.config.preferLoginWith = properties.preferLoginWith
    if (typeof properties.debug !== 'undefined') {
      window.App.setDebug(properties.debug)
    }
  }, onError)
}

ContextResolver.prototype.resolveAccount = function () {
  return User.getAccount().then(function (account) {
    window.App.config.connected = true
    window.App.config.account = account
    window.App.config.login = account.login
    window.App.config.userName = account.name
    window.App.config.timeZone = account.timeZone
    window.App.config.admin = account.admin

    var accountLocale = account.language || 'en'
    if (window.localStorage.locale !== accountLocale) {
      window.localStorage.locale = accountLocale
      window.location.reload()
    }

    return account
  }, onError)
}

ContextResolver.prototype.resolveWorkspaces = function () {
  return Workspace.getWorkspaces().then(function (workspaces) {
    window.App.config.workspaces = workspaces
    window.App.config.workspaceAdmin = _.findWhere(window.App.config.workspaces.administratedWorkspaces, { id: window.App.config.workspaceId }) !== undefined
    window.App.config.workspaces.nonAdministratedWorkspaces = _.reject(window.App.config.workspaces.allWorkspaces, function (workspace) {
      return _.contains(_.pluck(window.App.config.workspaces.administratedWorkspaces, 'id'), workspace.id)
    })
    return workspaces
  }, onError)
}

ContextResolver.prototype.resolveGroups = function () {
  return User.getGroups(window.App.config.workspaceId)
    .then(function (groups) {
      window.App.config.groups = groups
      window.App.config.isReadOnly = _.some(window.App.config.groups, function (group) {
        return group.readOnly
      }) && !window.App.config.workspaceAdmin
    }, onError)
}

ContextResolver.prototype.resolveOrganization = function () {
  return Organization.getOrganization().then(function (organization) {
    window.App.config.organization = organization || {}
  }, onError)
}

ContextResolver.prototype.resolveUser = function () {
  return User.whoami(window.App.config.workspaceId)
    .then(function (user) {
      window.App.config.user = user
    }, onError)
}

ContextResolver.prototype.resolveProviders = function () {
  return $.getJSON(window.App.config.apiEndPoint + '/auth/providers')
    .then(function (providers) {
      window.App.config.providers = providers.filter(function (provider) {
        return provider.enabled
      })
    })
}

export default new ContextResolver()
