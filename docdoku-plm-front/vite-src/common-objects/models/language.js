/**
 * Language 模型（ES Module 版）
 * 原：app/js/common-objects/models/language.js
 */
import $ from 'jquery'
import Backbone from 'backbone'

const Language = Backbone.Model.extend({
  initialize: function () {
    this.className = 'Language'
  }
})

Language.getLanguages = function () {
  return $.getJSON(window.App.config.apiEndPoint + '/languages')
}

export default Language
