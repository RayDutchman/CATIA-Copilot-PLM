/**
 * User 模型（ES Module 版）
 * 原：app/js/common-objects/models/user.js
 */
import $ from 'jquery'
import Backbone from 'backbone'

const UserModel = Backbone.Model.extend({
  getLogin: function () { return this.get('login') },
  getName: function () { return this.get('name') }
})

UserModel.whoami = function (workspaceId) {
  return $.getJSON(window.App.config.apiEndPoint + '/workspaces/' + workspaceId + '/users/me')
}

UserModel.getGroups = function (workspaceId) {
  return $.getJSON(window.App.config.apiEndPoint + '/workspaces/' + workspaceId + '/memberships/usergroups/me')
}

UserModel.getAccount = function () {
  return $.getJSON(window.App.config.apiEndPoint + '/accounts/me')
}

UserModel.updateAccount = function (account) {
  return $.ajax({
    type: 'PUT',
    url: window.App.config.apiEndPoint + '/accounts/me',
    data: JSON.stringify(account),
    contentType: 'application/json; charset=utf-8'
  })
}

UserModel.getTagSubscriptions = function (workspaceId, login) {
  return $.getJSON(window.App.config.apiEndPoint + '/workspaces/' + workspaceId + '/users/' + login + '/tag-subscriptions')
}

UserModel.addOrEditTagSubscription = function (workspaceId, login, tagSubscription, error) {
  return $.ajax({
    type: 'PUT',
    url: window.App.config.apiEndPoint + '/workspaces/' + workspaceId + '/users/' + login + '/tag-subscriptions/' + tagSubscription.getTag(),
    data: JSON.stringify(tagSubscription),
    contentType: 'application/json; charset=utf-8',
    error: error
  })
}

UserModel.removeTagSubscription = function (workspaceId, login, tagId, error) {
  return $.ajax({
    type: 'DELETE',
    url: window.App.config.apiEndPoint + '/workspaces/' + workspaceId + '/users/' + login + '/tag-subscriptions/' + tagId,
    error: error
  })
}

export default UserModel
