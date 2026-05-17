/**
 * Workspace 模型（ES Module 版）
 * 原：app/js/common-objects/models/workspace.js
 * 注意：原版部分方法使用了全局 _ (underscore)，此处补充 import
 */
import $ from 'jquery'
import _ from 'underscore'
import Backbone from 'backbone'

const Workspace = Backbone.Model.extend({
  initialize: function () {
    this.className = 'Workspace'
  }
})

const api = () => window.App.config.apiEndPoint

Workspace.getWorkspaces = function () {
  return $.getJSON(api() + '/workspaces')
}

Workspace.createWorkspace = function (workspace) {
  return $.ajax({ type: 'POST', url: api() + '/workspaces', data: JSON.stringify(workspace), contentType: 'application/json; charset=utf-8' })
}

Workspace.updateWorkspace = function (workspace) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspace.id, data: JSON.stringify(workspace), contentType: 'application/json; charset=utf-8' })
}

Workspace.deleteWorkspace = function (workspaceId) {
  return $.ajax({ type: 'DELETE', url: api() + '/workspaces/' + workspaceId })
}

Workspace.removeUsersFromWorkspace = function (workspaceId, userLogins) {
  var promiseArray = []
  _.each(userLogins, function (login) { promiseArray.push(Workspace.removeUserFromWorkspace(workspaceId, { login: login })) })
  return $.when.apply(undefined, promiseArray)
}

Workspace.removeUserFromWorkspace = function (workspaceId, user) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/remove-from-workspace', data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

Workspace.enableUser = function (workspaceId, user) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/enable-user', data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

Workspace.enableUsers = function (workspaceId, users) {
  var promiseArray = []
  _.each(users, function (user) { promiseArray.push(Workspace.enableUser(workspaceId, user)) })
  return $.when.apply(undefined, promiseArray)
}

Workspace.disableUsers = function (workspaceId, users) {
  var promiseArray = []
  _.each(users, function (user) { promiseArray.push(Workspace.disableUser(workspaceId, user)) })
  return $.when.apply(undefined, promiseArray)
}

Workspace.disableUser = function (workspaceId, user) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/disable-user', data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

Workspace.addUser = function (workspaceId, user, group) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/add-user' + (group ? '?group=' + group : ''), data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

Workspace.addGroup = function (workspaceId, group) {
  return $.ajax({ type: 'POST', url: api() + '/workspaces/' + workspaceId + '/user-group', data: JSON.stringify(group), contentType: 'application/json; charset=utf-8' })
}

Workspace.removeUserFromGroup = function (workspaceId, groupId, login) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/remove-from-group/' + groupId, data: JSON.stringify({ login: login }), contentType: 'application/json; charset=utf-8' })
}

Workspace.removeGroup = function (workspaceId, groupId) {
  return $.ajax({ type: 'DELETE', url: api() + '/workspaces/' + workspaceId + '/user-group/' + groupId })
}

Workspace.getUsersMemberships = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/memberships/users')
}

Workspace.getUsers = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/users')
}

Workspace.getUserGroupsMemberships = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/memberships/usergroups')
}

Workspace.setUsersMembership = function (workspaceId, membership) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/user-access', data: JSON.stringify(membership), contentType: 'application/json; charset=utf-8' })
}

Workspace.setGroupAccess = function (workspaceId, membership) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/group-access', data: JSON.stringify(membership), contentType: 'application/json; charset=utf-8' })
}

Workspace.getStatsOverView = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/stats-overview')
}

Workspace.getDiskUsageStats = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/disk-usage-stats')
}

Workspace.getCheckedOutDocumentsStats = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/checked-out-documents-stats')
}

Workspace.getCheckedOutPartsStats = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/checked-out-parts-stats')
}

Workspace.getUsersStats = function (workspaceId) {
  return $.when.apply(undefined, [
    $.getJSON(api() + '/workspaces/' + workspaceId + '/users').then(function (data) { return data }),
    $.getJSON(api() + '/workspaces/' + workspaceId + '/users-stats').then(function (data) { return data })
  ])
}

Workspace.setAdmin = function (workspaceId, login) {
  return $.ajax({ type: 'PUT', url: api() + '/workspaces/' + workspaceId + '/admin', data: JSON.stringify(login), contentType: 'application/json; charset=utf-8' })
}

Workspace.getUsersInGroups = function (args) {
  var groups = args.groups
  var next = args.next
  var promiseArray = []
  _.each(groups, function (group) {
    promiseArray.push($.getJSON(api() + '/workspaces/' + group.workspaceId + '/groups/' + group.memberId + '/users').then(function (users) { return next(group, users) }))
  })
  return $.when.apply(undefined, promiseArray)
}

Workspace.moveUsers = function (workspaceId, groupId, userLogins) {
  var promiseArray = []
  _.each(userLogins, function (login) { promiseArray.push(Workspace.addUser(workspaceId, { login: login }, groupId)) })
  return $.when.apply(undefined, promiseArray)
}

Workspace.getTags = function (workspaceId) {
  return $.getJSON(api() + '/workspaces/' + workspaceId + '/tags')
}

export default Workspace
