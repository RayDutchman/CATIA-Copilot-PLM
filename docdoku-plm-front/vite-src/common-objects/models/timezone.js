/**
 * TimeZone 模型（ES Module 版）
 * 原：app/js/common-objects/models/timezone.js
 */
import $ from 'jquery'
import Backbone from 'backbone'

const TimeZone = Backbone.Model.extend({
  initialize: function () {
    this.className = 'TimeZone'
  }
})

TimeZone.getTimeZones = function () {
  return $.getJSON(window.App.config.apiEndPoint + '/timezones')
}

export default TimeZone
