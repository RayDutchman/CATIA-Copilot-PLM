/**
 * 日志工具（ES Module 版）
 * 原：app/js/common-objects/log.js（AMD define，无外部依赖）
 * 迁移：去掉 define() 包装，直接 export default
 */

const colorCodes = {}

const contrast = function (rgb) {
  var o = Math.round(((parseInt(rgb[0]) * 299) + (parseInt(rgb[1]) * 587) + (parseInt(rgb[2]) * 114)) / 1000)
  return (o < 125) ? '#d4edf9' : '#14191f'
}

const generateColors = function (tag) {
  if (colorCodes[tag]) {
    return colorCodes[tag]
  }
  var num = Math.round(0xffffff * Math.random())
  var r = num >> 16
  var g = num >> 8 & 255
  var b = num & 255
  colorCodes[tag] = 'background: rgb(' + r + ', ' + g + ', ' + b + '); color:' + contrast([r, g, b])
  return colorCodes[tag]
}

const Logger = {
  log: function (tag, message) {
    if (window.App && window.App.debug) {
      if (!message) {
        message = tag
        tag = 'Logger'
      }
      window.console.log('%c [' + tag + '] ' + message, generateColors(tag))
    }
  }
}

export default Logger
