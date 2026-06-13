/*global define,App,window*/
define(function () {
    'use strict';

    var DEFAULT_CAMERA = {
        x: -1000,
        y: 800,
        z: 1100
    };

    function getUrlRoot() {
        var splitUrl = window.location.href.split('/');
        return splitUrl[0] + '//' + splitUrl[2];
    }

    function normalizeCamera(camera) {
        return {
            x: camera && camera.x !== undefined ? camera.x : DEFAULT_CAMERA.x,
            y: camera && camera.y !== undefined ? camera.y : DEFAULT_CAMERA.y,
            z: camera && camera.z !== undefined ? camera.z : DEFAULT_CAMERA.z
        };
    }

    function buildBaseVisualizationUrl(routeType, absolute) {
        var basePath = 'visualization/index.html#' + routeType + '/';
        return (absolute ? getUrlRoot() + '/' : App.config.contextPath) + basePath;
    }

    return {
        buildPartMasterUrl: function (workspaceId, partKey, camera, absolute) {
            var resolvedCamera = normalizeCamera(camera);
            return buildBaseVisualizationUrl('assembly', absolute) +
                workspaceId + '/' + partKey + '/' +
                resolvedCamera.x + '/' + resolvedCamera.y + '/' + resolvedCamera.z;
        },

        buildProductUrl: function (workspaceId, productId, camera, encodedPath, configSpec, absolute) {
            var resolvedCamera = normalizeCamera(camera);
            var url = buildBaseVisualizationUrl('product', absolute) +
                workspaceId + '/' + productId + '/' +
                resolvedCamera.x + '/' + resolvedCamera.y + '/' + resolvedCamera.z + '/';

            url += encodedPath ? encodedPath : '-1';

            if (configSpec) {
                url += '/' + configSpec;
            }

            return url;
        }
    };
});
