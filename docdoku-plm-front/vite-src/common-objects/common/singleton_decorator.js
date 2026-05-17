/**
 * Singleton 装饰器（ES Module 版）
 * 原：app/js/common-objects/common/singleton_decorator.js
 */
import _ from 'underscore'

// 给 constructor 添加 getInstance() 静态方法，确保全局唯一实例
const singletonDecorator = function (constructor) {
  constructor.getInstance = function () {
    if (!constructor._instance) {
      constructor._instance = _.extend(constructor.prototype, {})
      constructor.apply(constructor._instance, arguments)
    }
    return constructor._instance
  }
  return constructor
}

export default singletonDecorator
