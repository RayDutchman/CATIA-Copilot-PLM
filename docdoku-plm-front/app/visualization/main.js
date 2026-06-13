/*global $,require,window,_*/
var App = {};

require.config({

    urlArgs:'__BUST_CACHE__',

    baseUrl: '../product-structure/js',

    shim: {
        jqueryUI: { deps: ['jquery'], exports: 'jQuery' },
        bootstrap: { deps: ['jquery', 'jqueryUI'], exports: 'jQuery' },
        backbone: {deps: ['underscore', 'jquery'], exports: 'Backbone'}
    },
    paths: {
        jquery: '../../bower_components/jquery/jquery',
        jqueryUI: '../../bower_components/jqueryui/ui/jquery-ui',
        backbone: '../../bower_components/backbone/backbone',
        bootstrap:'../../bower_components/bootstrap/docs/assets/js/bootstrap',
        underscore: '../../bower_components/underscore/underscore',
        mustache: '../../bower_components/mustache/mustache',
        text: '../../bower_components/requirejs-text/text',
        i18n: '../../bower_components/requirejs-i18n/i18n',
        threecore: '../../bower_components/threejs/index',
        async: '../../bower_components/async/lib/async',
        tween:'../../bower_components/tweenjs/src/Tween',
        date:'../../bower_components/date.format/date.format',
        dat:'../../bower_components/dat.gui/dat.gui',
        localization: '../../js/localization',
        moment:'../../bower_components/moment/min/moment-with-locales',
        momentTimeZone:'../../bower_components/moment-timezone/builds/moment-timezone-with-data',
        'common-objects': '../../js/common-objects',
        transformcontrols: '../../js/dmu/controls/TransformControls',
        pointerlockcontrols: '../../js/dmu/controls/PointerLockControls',
        trackballcontrols: '../../js/dmu/controls/TrackballControls',
        orbitcontrols: '../../js/dmu/controls/OrbitControls',
        buffergeometryutils: '../../js/dmu/utils/BufferGeometryUtils',
        objloader: '../../js/dmu/loaders/OBJLoader',
        mtlloader: '../../js/dmu/loaders/MTLLoader',
        gltfloader: '../../js/dmu/loaders/GLTFLoader',
        stats:'../../js/dmu/utils/Stats',
        utilsprototype:'../../js/utils/utils.prototype',
        jwt_decode: '../../bower_components/jwt-decode/build/jwt-decode'
    },

    deps: [
        'stats',
        'dat',
        'utilsprototype',
        'bootstrap'
    ],
    config: {
        i18n: {
            locale: (function(){
	            'use strict';
                try{
                    var SUPPORTED = ['fr', 'ru', 'zh'];
                    var stored = window.localStorage.locale;
                    if (stored) { return stored; }
                    var nav = (navigator.language || navigator.userLanguage || '').split('-')[0].toLowerCase();
                    return SUPPORTED.indexOf(nav) !== -1 ? nav : 'en';
                }catch(ex){
                    return 'en';
                }
            })()
        }
    }
});

require(['common-objects/contextResolver','i18n!localization/nls/common','i18n!localization/nls/product-structure', 'common-objects/views/error'],
function (ContextResolver,  commonStrings, productStructureStrings, ErrorView) {

    'use strict';
    App.config.i18n = _.extend(commonStrings,productStructureStrings);

    App.config.workspaceId = decodeURIComponent(/^#(product|assembly)\/([^\/]+)/.exec(window.location.hash)[2]).trim() || null;
    App.config.productId = decodeURIComponent(window.location.hash.split('/')[2]).trim() || null;

    if (!App.config.workspaceId) {
        new ErrorView({el: '#content'})
            .renderWorkspaceSelection(ContextResolver.resolveServerProperties('..')
                .then(ContextResolver.resolveWorkspaces));
        return;
    }

    App.WorkerManagedValues = {
        maxInstances: 500,
        maxAngle: Math.PI,
        maxDist: 100000,
        minProjectedSize: 0.000001,//100,
        distanceRating: 0.6,//0.7,
        angleRating: 0.4,//0.6,//0.5,
        volRating: 1.0//0.7
    };

    App.SceneOptions = {
        grid: false,
        zoomSpeed: 1.2,
        rotateSpeed: 1.0,
        panSpeed: 0.3,
        cameraNear: 1,
        cameraFar: 5E4,
        defaultCameraPosition: {x: -1000, y: 800, z: 1100},
        defaultTargetPosition: {x: 0, y: 0, z: 0},
        ambientLightColor:0xffffff,
        cameraLight1Color:0xbcbcbc,
        cameraLight2Color:0xffffff,
        transformControls:false
    };

    ContextResolver.resolveServerProperties('..')
        .then(ContextResolver.resolveAccount)
        .then(ContextResolver.resolveWorkspaces)
        .then(ContextResolver.resolveGroups)
        .then(ContextResolver.resolveUser)
        .then(function(){
            require(['backbone', 'frameRouter', 'dmu/SceneManager','dmu/InstancesManager'],function(Backbone,  Router,SceneManager,InstancesManager){
                App.$SceneContainer = $('div#frameWorkspace');
                App.instancesManager = new InstancesManager();
                App.sceneManager = new SceneManager();
                App.sceneManager.init();
                App.router = Router.getInstance();
                Backbone.history.start();

                window._vizFit = function () {
                    try {
                        if (!App.sceneManager || !App.sceneManager.scene) {
                            return;
                        }

                        var minX = Infinity;
                        var maxX = -Infinity;
                        var minY = Infinity;
                        var maxY = -Infinity;
                        var minZ = Infinity;
                        var maxZ = -Infinity;
                        var found = false;

                        App.sceneManager.scene.traverse(function (obj) {
                            var parent = obj;

                            while (parent && !parent.partIterationId) {
                                parent = parent.parent;
                            }

                            if (!(obj.isMesh && obj.geometry && parent && parent.partIterationId)) {
                                return;
                            }

                            if (!obj.geometry.boundingBox) {
                                obj.geometry.computeBoundingBox();
                            }

                            var box = obj.geometry.boundingBox;
                            var matrix = obj.matrixWorld.elements;
                            var corners = [
                                [box.min.x, box.min.y, box.min.z],
                                [box.max.x, box.max.y, box.max.z],
                                [box.min.x, box.min.y, box.max.z],
                                [box.min.x, box.max.y, box.min.z],
                                [box.max.x, box.min.y, box.min.z],
                                [box.min.x, box.max.y, box.max.z],
                                [box.max.x, box.min.y, box.max.z],
                                [box.max.x, box.max.y, box.min.z]
                            ];

                            corners.forEach(function (point) {
                                var worldX = matrix[0] * point[0] + matrix[4] * point[1] + matrix[8] * point[2] + matrix[12];
                                var worldY = matrix[1] * point[0] + matrix[5] * point[1] + matrix[9] * point[2] + matrix[13];
                                var worldZ = matrix[2] * point[0] + matrix[6] * point[1] + matrix[10] * point[2] + matrix[14];

                                minX = Math.min(minX, worldX);
                                maxX = Math.max(maxX, worldX);
                                minY = Math.min(minY, worldY);
                                maxY = Math.max(maxY, worldY);
                                minZ = Math.min(minZ, worldZ);
                                maxZ = Math.max(maxZ, worldZ);
                                found = true;
                            });
                        });

                        if (!found) {
                            return;
                        }

                        var centerX = (minX + maxX) / 2;
                        var centerY = (minY + maxY) / 2;
                        var centerZ = (minZ + maxZ) / 2;
                        var maxDimension = Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1;
                        var fov = (App.sceneManager.cameraObject.fov || 45) * Math.PI / 180;
                        var distance = maxDimension / 2 / Math.tan(fov / 2) * 1.8;

                        App.sceneManager.setControlsContext({
                            camPos: {
                                x: centerX + distance * 0.5,
                                y: centerY + distance * 0.4,
                                z: centerZ + distance * 0.8
                            },
                            target: {
                                x: centerX,
                                y: centerY,
                                z: centerZ
                            },
                            camOrientation: App.sceneManager.cameraObject.up
                        });
                    } catch (err) {
                    }
                };

                setTimeout(function () {
                    $('#part-3d-nav-btns').remove();

                    var $nav = $('<div>').attr('id', 'part-3d-nav-btns').css({
                        position: 'absolute',
                        top: '8px',
                        right: '8px',
                        'z-index': '9999',
                        display: 'flex',
                        gap: '4px'
                    });
                    var $resetButton = $('<button>').addClass('btn btn-custom').attr('title', '重置相机')
                        .append($('<i>').addClass('fa fa-map-marker'));
                    var $fitButton = $('<button>').addClass('btn btn-custom').attr('title', '最佳适应视图')
                        .append($('<i>').addClass('fa fa-crosshairs'));

                    $resetButton.on('click', function (event) {
                        event.stopPropagation();
                        if (window._vizFit) {
                            window._vizFit();
                        }
                    });

                    $fitButton.on('click', function (event) {
                        event.stopPropagation();
                        if (window._vizFit) {
                            window._vizFit();
                        }
                    });

                    $nav.append($resetButton).append($fitButton);
                    $('body').append($nav);
                }, 0);

                window.addEventListener('message', function (event) {
                    if (!App.sceneManager) {
                        return;
                    }

                    if (event.data === 'resetCamera') {
                        App.sceneManager.resetCameraPlace();
                    } else if (event.data === 'bestFit' && window._vizFit) {
                        window._vizFit();
                    }
                });
            });
        },function(xhr){
            new ErrorView({el:'#content'}).renderError(xhr);
        });
});
