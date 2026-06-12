/*global _,define,App*/
define(['threecore', 'gltfloader', 'views/progress_bar_view'], function (THREE, GLTFLoader, ProgressBarView) {
    'use strict';

    var LoaderManager = function (options) {
        _.extend(this, options);
        if (this.progressBar) {
            this.listenXHRProgress();
        }
    };

    function setShadows(object) {
        if (object instanceof THREE.Object3D) {
            object.traverse(function (o) {
                if (o instanceof THREE.Mesh) {
                    o.castShadow = true;
                    o.receiveShadow = true;
                }
            });
        }
    }

    LoaderManager.prototype = {

        listenXHRProgress: function () {

            var pbv = new ProgressBarView().render();
            var _xhrOpen = XMLHttpRequest.prototype.open;

            XMLHttpRequest.prototype.open = function () {

                var isGeometryRequest = arguments[1].indexOf(App.config.serverBasePath + 'api/files/') === 0;

                if (isGeometryRequest) {

                    var totalAdded = false,
                        totalLoaded = 0,
                        xhrLength = 0;

                    this.addEventListener('loadstart', function () {}, false);

                    this.addEventListener('progress', function (pe) {

                        if (xhrLength === 0) {
                            xhrLength = pe.total;
                        }

                        if (totalAdded === false) {
                            pbv.addTotal(xhrLength);
                            totalAdded = true;
                        }

                        pbv.addLoaded(pe.loaded - totalLoaded);
                        totalLoaded = pe.loaded;

                    }, false);

                    this.addEventListener('loadend', function () {
                        setTimeout(function () {
                            pbv.removeXHRData(xhrLength);
                        }, 20);
                    }, false);
                }

                _xhrOpen.apply(this, arguments);

                // Disable compression for geometry files
                if (isGeometryRequest) {
                    this.setRequestHeader('x-accept-encoding', 'identity');
                }
            };
        },

        parseFile: function (filename, texturePath, callbacks) {
            var loader = new GLTFLoader();
            loader.load(
                filename,
                function (gltf) {
                    var object = gltf.scene;
                    setShadows(object);
                    callbacks.success(object);
                },
                undefined,
                function (err) {
                    console.error('GLTFLoader error:', err);
                    if (callbacks.error) {
                        callbacks.error(err);
                    }
                }
            );
        }
    };

    return LoaderManager;
});
