/*global define,App*/
define([
    'backbone',
    'mustache',
    'text!common-objects/templates/part/cad_instance.html'
], function (Backbone, Mustache, template) {
	'use strict';
    var CadInstanceView = Backbone.View.extend({

        className: 'cad-instance',

        events: {
            'change input[name=tx]': 'changeTX',
            'change input[name=ty]': 'changeTY',
            'change input[name=tz]': 'changeTZ',
            'change input[name=rx]': 'changeRX',
            'change input[name=ry]': 'changeRY',
            'change input[name=rz]': 'changeRZ',
            'change input':'onChange',
            'click .delete-cad-instance': 'removeCadInstance'
        },

        initialize: function () {
        },

        render: function () {
            var disabled = this.options.editMode ? '':'disabled';
            // 对极小浮点噪声（|v| < 1e-10）归零，避免 -9.8e-15 这类 CATIA 计算残差
            // 在固定宽度输入框中被截断显示为误导性的非零值（BUG-41）
            var attrs = this.model.attributes;
            var instance = {
                tx: Math.abs(attrs.tx) < 1e-10 ? 0 : attrs.tx,
                ty: Math.abs(attrs.ty) < 1e-10 ? 0 : attrs.ty,
                tz: Math.abs(attrs.tz) < 1e-10 ? 0 : attrs.tz,
                rx: Math.abs(attrs.rx) < 1e-10 ? 0 : attrs.rx,
                ry: Math.abs(attrs.ry) < 1e-10 ? 0 : attrs.ry,
                rz: Math.abs(attrs.rz) < 1e-10 ? 0 : attrs.rz
            };
            this.$el.html(Mustache.render(template, {
                canRemove:this.options.editMode,
                disabled:disabled,
                instance: instance,
                i18n: App.config.i18n
            }));
            return this;
        },

        changeTX: function (e) {
            this.model.set('tx', e.target.value);
        },

        changeTY: function (e) {
            this.model.set('ty',e.target.value);
        },

        changeTZ: function (e) {
            this.model.set('tz', e.target.value);
        },

        changeRX: function (e) {
            this.model.set('rx', e.target.value);
        },

        changeRY: function (e) {
            this.model.set('ry', e.target.value);
        },

        changeRZ: function (e) {
            this.model.set('rz', e.target.value);
        },

        removeCadInstance: function () {
            this.model.collection.remove(this.model);
            this.remove();
        }

    });

    return CadInstanceView;
});
