/**
 * Organization 模型（ES Module 版）
 * 原：app/js/common-objects/models/organization.js
 */
import $ from 'jquery'
import _ from 'underscore'
import Backbone from 'backbone'

const Organization = Backbone.Model.extend({
  initialize: function () {
    this.className = 'Organization'
  }
})

const api = () => window.App.config.apiEndPoint

Organization.getOrganization = function () {
  return $.getJSON(api() + '/organizations')
}

Organization.createOrganization = function (organization) {
  return $.ajax({ type: 'POST', url: api() + '/organizations', data: JSON.stringify(organization), contentType: 'application/json; charset=utf-8' })
}

Organization.updateOrganization = function (organization) {
  return $.ajax({ type: 'PUT', url: api() + '/organizations', data: JSON.stringify(organization), contentType: 'application/json; charset=utf-8' })
}

Organization.deleteOrganization = function () {
  return $.ajax({ type: 'DELETE', url: api() + '/organizations', contentType: 'application/json; charset=utf-8' })
}

Organization.getMembers = function () {
  return $.getJSON(api() + '/organizations/members')
}

Organization.addMember = function (user) {
  return $.ajax({ type: 'PUT', url: api() + '/organizations/add-member', data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

Organization.removeMember = function (user) {
  return $.ajax({ type: 'PUT', url: api() + '/organizations/remove-member', data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

Organization.removeMembers = function (userLogins) {
  var promiseArray = []
  _.each(userLogins, function (login) { promiseArray.push(Organization.removeMember({ login: login })) })
  return $.when.apply(undefined, promiseArray)
}

Organization.moveMemberUp = function (user) {
  return $.ajax({ type: 'PUT', url: api() + '/organizations/move-member?direction=up', data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

Organization.moveMemberDown = function (user) {
  return $.ajax({ type: 'PUT', url: api() + '/organizations/move-member?direction=down', data: JSON.stringify(user), contentType: 'application/json; charset=utf-8' })
}

export default Organization
