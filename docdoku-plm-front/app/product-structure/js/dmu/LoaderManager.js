/*global _,define,App*/
define(['threecore', 'objloader', 'mtlloader', 'views/progress_bar_view'], function (THREE, OBJLoader, MTLLoader, ProgressBarView) {
    'use strict';
    var LoaderManager = function (options) {
        _.extend(this, options);
        if (this.progressBar) {
            this.listenXHRProgress();
        }
    };

    var defaultMaterial = new THREE.MeshLambertMaterial({color: new THREE.Color(0xcccccc)});

    function setShadows(object) {
        if (object instanceof THREE.Object3D) {
            object.traverse(function (o) {
                if (o instanceof THREE.Mesh) {
                    o.castShadow = true;
                    o.receiveShadow = true;
                }
            });
        } else if (object instanceof THREE.Mesh) {
            object.castShadow = true;
            object.receiveShadow = true;
        }
    }

    function updateMaterial(object) {
        if (object instanceof THREE.Object3D) {
            object.traverse(function (o) {
                if (o instanceof THREE.Mesh && !o.material.name) {
                    o.material = defaultMaterial;
                }
            });
        } else if (object instanceof THREE.Mesh && !object.material.name) {
            object.castShadow = true;
            object.receiveShadow = true;
        }
    }

    LoaderManager.prototype = {

        listenXHRProgress: function () {

            // Override xhr open prototype
            var pbv = new ProgressBarView().render();
            var xhrCount = 0;
            var _xhrOpen = XMLHttpRequest.prototype.open;

            XMLHttpRequest.prototype.open = function () {

                // Subscribe only to files requests
                var isGeometryRequest = arguments[1].indexOf(App.config.serverBasePath + 'api/files/') === 0;

                if (isGeometryRequest) {

                    var totalAdded = false,
                        totalLoaded = 0,
                        xhrLength = 0;

                    this.addEventListener('loadstart', function () {
                        xhrCount++;
                    }, false);

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
                        xhrCount--;
                        setTimeout(function () {
                            pbv.removeXHRData(xhrLength);
                        }, 20);
                    }, false);
                }

                _xhrOpen.apply(this, arguments);

                // Force server to send the file without compression (custom header)
                if (isGeometryRequest) {
                    this.setRequestHeader('x-accept-encoding', 'identity');
                }

            };
        },


        parseFile: function (filename, texturePath, callbacks) {
            // Derive MTL filename from OBJ filename (same base name, .mtl extension)
            // MTL and textures are stored under the attachedfiles/ sub-path
            var fileShortName = filename.split('?')[0];
            fileShortName = fileShortName.substr(fileShortName.lastIndexOf('/') + 1);
            var mtlFile = fileShortName.substr(0, fileShortName.lastIndexOf('.')) + '.mtl';
            var mtlBasePath = texturePath.substr(0, texturePath.lastIndexOf('/') + 1) + 'attachedfiles/';

            function loadOBJ(materials) {
                var objLoader = new OBJLoader();
                if (materials && typeof materials.preload === 'function') {
                    materials.preload();
                    objLoader.setMaterials(materials);
                }
                objLoader.load(filename, function (object) {
                    setShadows(object);
                    // Only apply default material to meshes that have no named material
                    updateMaterial(object);
                    callbacks.success(object);
                });
            }

            // Try to load MTL first; fall back gracefully if not found
            try {
                // JWT is sent via Authorization header by contextResolver.js,
                // pass null so MTLLoader does not append a redundant ?token= param
                var mtlLoader = new MTLLoader(null);
                mtlLoader.setPath(mtlBasePath);
                mtlLoader.load(mtlFile, loadOBJ, null, function () {
                    // MTL not found or failed — load OBJ without materials
                    loadOBJ(null);
                });
            } catch (e) {
                loadOBJ(null);
            }
        }
    };
    return LoaderManager;
});
