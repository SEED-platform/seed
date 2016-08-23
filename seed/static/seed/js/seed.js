/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * AngularJS app 'config.seed' for SEED SPA
 */

angular.module('BE.seed.angular_dependencies', [
    'ngRoute',
    'ngCookies'
    ]);
angular.module('BE.seed.vendor_dependencies', [
    'ui.bootstrap',
    'ui.grid',
    'ui.grid.exporter',
    'ui.grid.grouping',
    'ui.grid.moveColumns',
    'ui.grid.pinning',
    'ui.grid.resizeColumns',
    'ui.grid.saveState',
    'ui.grid.selection',
    'ui.grid.treeView',
    'ui.sortable',
    'ui.tree',
    'xeditable',
    'ngTagsInput',
    'ui-notification'
    ]);
angular.module('BE.seed.controllers', [
    'BE.seed.controller.about',
    'BE.seed.controller.accounts',
    'BE.seed.controller.admin',
    'BE.seed.controller.api',
    'BE.seed.controller.building_detail',
    'BE.seed.controller.building_detail_update_labels_modal_ctrl',
    'BE.seed.controller.building_list',
    'BE.seed.controller.buildings_reports',
    'BE.seed.controller.buildings_settings',
    'BE.seed.controller.cleansing',
    'BE.seed.controller.cleansing_admin',
    'BE.seed.controller.concat_modal',
    'BE.seed.controller.create_note_modal',
    'BE.seed.controller.create_organization_modal',
    'BE.seed.controller.data_upload_modal',
    'BE.seed.controller.dataset',
    'BE.seed.controller.dataset_detail',
    'BE.seed.controller.delete_modal',
    'BE.seed.controller.developer',
    'BE.seed.controller.edit_project_modal',
    'BE.seed.controller.existing_members_modal',
    'BE.seed.controller.export_modal',
    'BE.seed.controller.label_admin',
    'BE.seed.controller.mapping',
    'BE.seed.controller.matching',
    'BE.seed.controller.matching_detail',
    'BE.seed.controller.members',
    'BE.seed.controller.menu',
    'BE.seed.controller.new_member_modal',
    'BE.seed.controller.profile',
    'BE.seed.controller.organization',
    'BE.seed.controller.organization_settings',
    'BE.seed.controller.project',
    'BE.seed.controller.update_building_labels_modal',
    'BE.seed.controller.security',
    'BE.seed.controller.bluesky_properties_controller',
    'BE.seed.controller.bluesky_taxlots_controller'
    ]);
angular.module('BE.seed.filters', [
    'district',
    'fromNow',
    'ignoremap',
    'stripImportPrefix',
    'titleCase',
    'typedNumber'
    ]);
angular.module('BE.seed.directives', [
    'sdEnter',
    'sdUploader',
    'sdLabel',
    'sdResizable',
    'sdBasicBuildingInfoChart',
    'sdDropdown',
    'sdCheckLabelExists'
    ]);
angular.module('BE.seed.services', [
    'BE.seed.service.audit',
    'BE.seed.service.auth',
    'BE.seed.service.building',
    'BE.seed.service.buildings_reports',
    'BE.seed.service.cleansing',
    'BE.seed.service.dataset',
    'BE.seed.service.export',
    'BE.seed.service.label',
    'BE.seed.service.main',
    'BE.seed.service.mapping',
    'BE.seed.service.matching',
    'BE.seed.service.organization',
    'BE.seed.service.project',
    'BE.seed.service.uploader',
    'BE.seed.service.user',
    'mappingValidatorService',
    'BE.seed.service.search',
    'BE.seed.service.simple_modal',
    'BE.seed.service.httpParamSerializerSeed',
    'BE.seed.service.bluesky_service'
    ]);
angular.module('BE.seed.utilities', [
    'BE.seed.utility.spinner'
    ]);

var SEED_app = angular.module('BE.seed', [
    'BE.seed.angular_dependencies',
    'BE.seed.vendor_dependencies',
    'BE.seed.filters',
    'BE.seed.directives',
    'BE.seed.services',
    'BE.seed.controllers',
    'BE.seed.utilities'
], ['$interpolateProvider', function ($interpolateProvider) {
        $interpolateProvider.startSymbol('{$');
        $interpolateProvider.endSymbol('$}');
    }]
);

/**
 * Adds the Django CSRF token to all $http requests
 */
SEED_app.run([
  '$http',
  '$cookies',
  'editableOptions',
  function ($http, $cookies, editableOptions) {
    var csrftoken = $cookies.get('csrftoken');
    BE.csrftoken = csrftoken;
    $http.defaults.headers.common['X-CSRFToken'] = csrftoken;
    $http.defaults.headers.post['X-CSRFToken'] = csrftoken;
    $http.defaults.xsrfCookieName = 'csrftoken';
    $http.defaults.xsrfHeaderName = 'X-CSRFToken';

    //config ANGULAR-XEDITABLE ... (this is the recommended place rather than in .config)...
    editableOptions.theme = 'bs3';
  }
]);

/**
 * url routing declaration for SEED
 */
SEED_app.config(['$routeProvider', function ($routeProvider) {

    var static_url = BE.urls.STATIC_URL;

    $routeProvider
        .when('/', {
            templateUrl: static_url + 'seed/partials/home.html'
        })
        .when('/profile', {
            templateUrl: static_url + 'seed/partials/profile.html',
            controller: 'profile_controller',
            resolve: {
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_superuser']);
                }],
                user_profile_payload: ['user_service', function (user_service) {
                    return user_service.get_user_profile();
                }]
            }
        })
        .when('/profile/security', {
            templateUrl: static_url + 'seed/partials/security.html',
            controller: 'security_controller',
            resolve: {
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_superuser']);
                }],
                user_profile_payload: ['user_service', function (user_service) {
                    return user_service.get_user_profile();
                }]
            }
        })
        .when('/profile/developer', {
            templateUrl: static_url + 'seed/partials/developer.html',
            controller: 'developer_controller',
            resolve: {
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_superuser']);
                }],
                user_profile_payload: ['user_service', function (user_service) {
                    return user_service.get_user_profile();
                }]
            }
        })
        .when('/profile/admin', {
            templateUrl: static_url + 'seed/partials/admin.html',
            controller: 'seed_admin_controller',
            resolve: {
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_superuser'])
                    .then(function (data) {
                        if (data.auth.requires_superuser){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }],
                user_profile_payload: ['user_service', function (user_service) {
                    return user_service.get_user_profile();
                }]
            }
        })
        .when('/projects', {
            controller: 'project_list_controller',
            templateUrl: static_url + 'seed/partials/projects.html',
            resolve: {
                projects_payload: ['project_service', function(project_service) {
                    return project_service.get_projects();
                }]
            }
        })
        .when('/projects/:project_id', {
            controller: 'building_list_controller',
            templateUrl: static_url + 'seed/partials/project_detail.html',
            resolve: {
                search_payload: ['building_services', '$route', function(building_services, $route){
                    var orderBy = '';
                    var sortReverse = false;
                    var params = angular.copy($route.current.params);
                    var q = params.q || '';
                    var numberPerPage = 10;
                    var project_slug = params.project_id;
                    var pageNumber = 1;
                    delete(params.project_id);
                    params.project__slug = project_slug;

                    // Check session storage for order, sort, and filter values.
                    if (!_.isUndefined(Storage)) {

                        // set the prefix to the specific project. This fixes
                        // the issue where the filter was not persisting.
                        var prefix = _.replace($route.current.$$route.originalPath, ':project_id', project_slug);
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy') !== null) {
                            orderBy = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse') !== null) {
                            sortReverse = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse'));
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams') !== null) {
                            params = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams'));
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage') !== null) {
                            numberPerPage = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage'));
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingPageNumber') !== null) {
                            pageNumber = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingPageNumber'));
                        }
                    }
                    // params: (query_string, number_per_page, page_number, order_by, sort_reverse, filter_params, project_id, project_slug)
                    return building_services.search_buildings(q, numberPerPage, pageNumber, orderBy, sortReverse, params, null, project_slug);
                }],
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_columns();
                }],
                all_columns: ['building_services', '$route', function(building_services, $route) {
                    var params = angular.copy($route.current.params);
                    var project_slug = params.project_id;
                    return building_services.get_columns();
                }],
                project_payload: ['$route', 'project_service', function($route, project_service) {
                    var params = angular.copy($route.current.params);
                    var project_slug = params.project_id;
                    return project_service.get_project(project_slug);
                }]
            }
        })
        .when('/projects/:project_id/settings', {
            templateUrl: static_url + 'seed/partials/project_settings.html',
            controller: 'buildings_settings_controller',
            resolve: {
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_columns();
                }],
                shared_fields_payload: ['user_service', '$route', function(user_service, $route) {
                    return user_service.get_shared_buildings();
                }],
                $uibModalInstance: function() {
                    return {close: function () {}};
                },
                project_payload: ['$route', 'project_service', function($route, project_service) {
                    var params = angular.copy($route.current.params);
                    var project_slug = params.project_id;
                    return project_service.get_project(project_slug);
                }],
                building_payload: function() {
                    return {building: {}};
                }
            }
        })
        .when('/projects/:project_id/:building_id', {
            controller: 'building_detail_controller',
            resolve: {
                building_payload: ['building_services', '$route', function(building_services, $route){
                    var building_id = $route.current.params.building_id;
                    return building_services.get_building(building_id);
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                audit_payload: function(){
                    return {audit_logs: {}};
                },
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_building_detail_columns();
                }]
            },
            templateUrl: static_url + 'seed/partials/building_detail_section.html'
        })
        .when('/buildings', {
            controller: 'building_list_controller',
            templateUrl: static_url + 'seed/partials/buildings.html',
            resolve: {
                search_payload: ['building_services', '$route', function(building_services, $route){
                    // Defaults
                    var q = $route.current.params.q || '';
                    var orderBy = '';
                    var sortReverse = false;
                    var params = {};
                    var numberPerPage = 10;
                    var pageNumber = 1;

                    // Check session storage for order, sort, and filter values.
                    if (!_.isUndefined(Storage)) {

                        var prefix = $route.current.$$route.originalPath;

                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy') !== null) {
                            orderBy = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse') !== null) {
                            sortReverse = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse'));
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams') !== null) {
                            params = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams'));
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage') !== null) {
                            numberPerPage = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage'));
                        }
                        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingPageNumber') !== null) {
                            pageNumber = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingPageNumber'));
                        }
                    }

                    // params: (query, number_per_page, page_number, order_by, sort_reverse, filter_params, project_id)
                    return building_services.search_buildings(q, numberPerPage, pageNumber, orderBy, sortReverse, params, null);
                }],
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_columns();
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                project_payload: function() {
                    return {
                        project: {}
                    };
                }
            }
        })
        .when('/buildings/settings', {
            templateUrl: static_url + 'seed/partials/buildings_settings.html',
            controller: 'buildings_settings_controller',
            resolve: {
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_columns();
                }],
                shared_fields_payload: ['user_service', '$route', function(user_service, $route) {
                    return user_service.get_shared_buildings();
                }],
                $uibModalInstance: function() {
                    return {close: function () {}};
                },
                project_payload: function() {
                    return {project: {}};
                },
                building_payload: function() {
                    return {building: {}};
                }
            }

        })
        .when('/buildings/reports', {
            templateUrl: static_url + 'seed/partials/buildings_reports.html',
            controller: 'buildings_reports_controller'
        })
        .when('/buildings/labels', {
            templateUrl: static_url + 'seed/partials/buildings_label_admin.html',
            controller: 'label_admin_controller'
        })
        .when('/buildings/:building_id', {
            controller: 'building_detail_controller',
            templateUrl: static_url + 'seed/partials/building_detail_section.html',
            resolve: {
                building_payload: ['building_services', '$route', function(building_services, $route){
                    // load `get_building` before page is loaded to avoid
                    // page flicker.
                    var building_id = $route.current.params.building_id;
                    return building_services.get_building(building_id);
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                audit_payload: function(){
                    return {audit_logs: {}};
                },
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_building_detail_columns();
                }]
            }
        })
        .when('/buildings/:building_id/projects', {
            controller: 'building_detail_controller',
            templateUrl: static_url + 'seed/partials/building_projects_section.html',
            resolve: {
                building_payload: ['building_services', '$route', function(building_services, $route){
                    // load `get_building` before page is loaded to avoid
                    // page flicker.
                    var building_id = $route.current.params.building_id;
                    return building_services.get_building(building_id);
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                audit_payload: function(){
                    return {audit_logs: {}};
                },
                default_columns: function(){
                    return {columns: {}};
                }
            }
        })
        .when('/buildings/:building_id/audit', {
            controller: 'building_detail_controller',
            templateUrl: static_url + 'seed/partials/building_audit_log.html',
            resolve: {
                building_payload: ['building_services', '$route', function(building_services, $route){
                    // load `get_building` before page is loaded to avoid
                    // page flicker.
                    var building_id = $route.current.params.building_id;
                    return building_services.get_building(building_id);
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                audit_payload: ['audit_service', '$route', function(audit_service, $route){
                    var building_id = $route.current.params.building_id;
                    return audit_service.get_building_logs(building_id);
                }],
                default_columns: function(){
                    return {columns: {}};
                }
            }
        })
        .when('/buildings/:building_id/energy', {
            controller: 'building_detail_controller',
            templateUrl: static_url + 'seed/partials/building_energy_section.html',
            resolve: {
                building_payload: ['building_services', '$route', function(building_services, $route){
                    // load `get_building` before page is loaded to avoid
                    // page flicker.
                    var building_id = $route.current.params.building_id;
                    return building_services.get_building(building_id);
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                audit_payload: function(){
                    return {audit_logs: {}};
                },
                default_columns: function(){
                    return {columns: {}};
                }
            }
        })
        .when('/buildings/:building_id/settings', {
            controller: 'buildings_settings_controller',
            templateUrl: static_url + 'seed/partials/building_settings_section.html',
            resolve: {
                building_payload: ['building_services', '$route', function(building_services, $route){
                    // load `get_building` before page is loaded to avoid
                    // page flicker.
                    var building_id = $route.current.params.building_id;
                    return building_services.get_building(building_id);
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_building_detail_columns();
                }],
                shared_fields_payload: ['user_service', '$route', function(user_service, $route) {
                    return {show_shared_buildings: false};
                }],
                $uibModalInstance: function() {
                    return {close: function () {}};
                },
                project_payload: function() {
                    return {project: {}};
                }
            }
        })
        .when('/data/mapping/:importfile_id', {
            controller: 'mapping_controller',
            templateUrl: static_url + 'seed/partials/mapping.html',
            resolve: {
                import_file_payload: ['dataset_service', '$route', function(dataset_service, $route){
                    var importfile_id = $route.current.params.importfile_id;
                    return dataset_service.get_import_file(importfile_id);
                }],
                suggested_mappings_payload: ['mapping_service', '$route', function(mapping_service, $route){
                    var importfile_id = $route.current.params.importfile_id;
                    return mapping_service.get_column_mapping_suggestions(
                        importfile_id
                    );
                }],
                raw_columns_payload: ['mapping_service', '$route', function(mapping_service, $route){
                    var importfile_id = $route.current.params.importfile_id;
                    return mapping_service.get_raw_columns(
                        importfile_id
                    );
                }],
                first_five_rows_payload: ['mapping_service', '$route', function(mapping_service, $route){
                    var importfile_id = $route.current.params.importfile_id;
                    return mapping_service.get_first_five_rows(
                        importfile_id
                    );
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_member'])
                    .then(function (data) {
                        if (data.auth.requires_member){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/data/matching/:importfile_id', {
            controller: 'matching_controller',
            templateUrl: static_url + 'seed/partials/matching.html',
            resolve: {
                import_file_payload: ['dataset_service', '$route', function(dataset_service, $route){
                    var importfile_id = $route.current.params.importfile_id;
                    return dataset_service.get_import_file(importfile_id);
                }],
                buildings_payload: ['building_services', '$route', function(building_services, $route){
                    var importfile_id = $route.current.params.importfile_id;
                    return building_services.search_matching_buildings(
                        '', 10, 1, '', false, {}, importfile_id);
                }],
                default_columns: ['user_service', function(user_service){
                    return user_service.get_default_columns();
                }],
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_member'])
                    .then(function (data) {
                        if (data.auth.requires_member){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/data/:dataset_id', {
            controller: 'dataset_detail_controller',
            templateUrl: static_url + 'seed/partials/dataset_detail.html',
            resolve: {
                dataset_payload: ['dataset_service', '$route', function(dataset_service, $route){
                    var dataset_id = $route.current.params.dataset_id;
                    return dataset_service.get_dataset(dataset_id);
                }],
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_member'])
                    .then(function (data) {
                        if (data.auth.requires_member){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/data', {
            controller: 'dataset_list_controller',
            templateUrl: static_url + 'seed/partials/dataset_list.html',
            resolve: {
                datasets_payload: ['dataset_service', '$route', function(dataset_service, $route){
                    return dataset_service.get_datasets();
                }],
                auth_payload: ['auth_service', '$q', 'user_service', function(auth_service, $q, user_service) {
                    var organization_id = user_service.get_organization().id;
                    return auth_service.is_authorized(organization_id, ['requires_member'])
                    .then(function (data) {
                        if (data.auth.requires_member){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/feedback', {
            templateUrl: static_url + 'seed/partials/feedback.html'
        })
        .when('/api-docs', {
            controller: 'api_controller',
            templateUrl: static_url + 'seed/partials/api_docs.html'
        })
        .when('/about', {
            controller: 'about_controller',
            templateUrl: static_url + 'seed/partials/about.html',
            resolve: {
                version_payload: ['main_service', function (main_service) {
                    return main_service.version();
                }]
            }
        })
        .when('/accounts', {
            controller: 'accounts_controller',
            templateUrl: static_url + 'seed/partials/accounts.html',
            resolve: {
                organization_payload: ['organization_service', function (organization_service) {
                    return organization_service.get_organizations();
                }]
            }
        })
        .when('/accounts/:organization_id', {
            controller: 'settings_controller',
            templateUrl: static_url + 'seed/partials/settings.html',
            resolve: {
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns(true);
                }],
                organization_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_organization(organization_id);
                }],
                query_threshold_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_query_threshold(organization_id);
                }],
                shared_fields_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_shared_fields(organization_id);
                }],
                auth_payload: ['auth_service', '$route', '$q', function(auth_service, $route, $q) {
                    var organization_id = $route.current.params.organization_id;
                    return auth_service.is_authorized(organization_id, ['requires_owner'])
                    .then(function (data) {
                        if (data.auth.requires_owner){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/accounts/:organization_id/sharing', {
            controller: 'settings_controller',
            templateUrl: static_url + 'seed/partials/sharing.html',
            resolve: {
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                organization_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_organization(organization_id);
                }],
                query_threshold_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_query_threshold(organization_id);
                }],
                shared_fields_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_shared_fields(organization_id);
                }],
                auth_payload: ['auth_service', '$route', '$q', function(auth_service, $route, $q) {
                    var organization_id = $route.current.params.organization_id;
                    return auth_service.is_authorized(organization_id, ['requires_owner'])
                    .then(function (data) {
                        if (data.auth.requires_owner){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/accounts/:organization_id/data_cleansing', {
            controller: 'cleansing_admin_controller',
            templateUrl: static_url + 'seed/partials/cleansing_admin.html',
            resolve: {
                all_columns: ['building_services', function(building_services) {
                    return building_services.get_columns();
                }],
                organization_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_organization(organization_id);
                }],
                cleansing_rules_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_cleansing_rules(organization_id);
                }],
                auth_payload: ['auth_service', '$route', '$q', function(auth_service, $route, $q) {
                    var organization_id = $route.current.params.organization_id;
                    return auth_service.is_authorized(organization_id, ['requires_owner'])
                    .then(function (data) {
                        if (data.auth.requires_owner){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/accounts/:organization_id/sub_org', {
            controller: 'organization_controller',
            templateUrl: static_url + 'seed/partials/sub_org.html',
            resolve: {
                users_payload: ['organization_service', '$route', function (organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_organization_users({org_id: organization_id});
                }],
                organization_payload: ['organization_service', '$route', '$q', function(organization_service, $route, $q) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_organization(organization_id)
                    .then(function (data){
                        if (data.organization.is_parent) {
                            return data;
                        } else {
                            return $q.reject('Your page could not be located!');
                        }
                    });
                }],
                auth_payload: ['auth_service', '$route', '$q', function(auth_service, $route, $q) {
                    var organization_id = $route.current.params.organization_id;
                    return auth_service.is_authorized(organization_id, ['requires_owner'])
                    .then(function (data) {
                        if (data.auth.requires_owner){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }]
            }
        })
        .when('/accounts/:organization_id/members', {
            controller: 'members_controller',
            templateUrl: static_url + 'seed/partials/members.html',
            resolve: {
                users_payload: ['organization_service', '$route', function (organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_organization_users({org_id: organization_id});
                }],
                organization_payload: ['organization_service', '$route', function(organization_service, $route) {
                    var organization_id = $route.current.params.organization_id;
                    return organization_service.get_organization(organization_id);
                }],
                auth_payload: ['auth_service', '$route', '$q', function(auth_service, $route, $q) {
                    var organization_id = $route.current.params.organization_id;
                    return auth_service.is_authorized(organization_id, ['can_invite_member', 'can_remove_member', 'requires_owner', 'requires_member'])
                    .then(function (data) {
                        if (data.auth.requires_member){
                            return data;
                        } else {
                            return $q.reject('not authorized');
                        }
                    }, function (data) {
                        return $q.reject(data.message);
                    });
                }],
                user_profile_payload: ['user_service', function (user_service) {
                    return user_service.get_user_profile();
                }]
            }
        })
        .when('/labels', {
            controller: 'labels_controller',
            templateUrl: static_url + 'seed/partials/labels.html'
        })
        .when('/bluesky/properties', {
            controller: 'bluesky_properties_controller',
            templateUrl: static_url + 'seed/partials/bluesky/list.html',
            resolve: {
                properties: ['bluesky_service', function(bluesky_service){
                    return bluesky_service.get_properties(1);
                }],
                cycles: ['bluesky_service', function(bluesky_service){
                    return bluesky_service.get_cycles();
                }],
                columns: ['bluesky_service', function(bluesky_service){
                    return bluesky_service.get_property_columns();
                }]
            }
        })
        .when('/bluesky/taxlots', {
            controller: 'bluesky_taxlots_controller',
            templateUrl: static_url + 'seed/partials/bluesky/list.html',
            resolve: {
                taxlots: ['bluesky_service', function(bluesky_service){
                    return bluesky_service.get_taxlots(1);
                }],
                cycles: ['bluesky_service', function(bluesky_service){
                    return bluesky_service.get_cycles();
                }],
                columns: ['bluesky_service', function(bluesky_service){
                    return bluesky_service.get_taxlot_columns();
                }]
            }
        })
        .otherwise({ redirectTo: '/' });

}]);

/**
 * whitelist needed to load html partials from Amazon AWS S3
 * defaults to 'self' otherwise
 */
SEED_app.config([
  '$sceDelegateProvider',
  'NotificationProvider',
  function ($sceDelegateProvider, NotificationProvider) {
    $sceDelegateProvider.resourceUrlWhitelist([
      'self',
      '**'
    ]);

    //config ANGULAR-UI-NOTIFICATION...
    var static_url = BE.urls.STATIC_URL;
    NotificationProvider.setOptions({
        templateUrl: static_url + 'seed/partials/custom_notification_template.html'
    });
  }
]);

SEED_app.config([
    '$httpProvider',
    function($httpProvider) {
    $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
    $httpProvider.defaults.paramSerializer = 'httpParamSerializerSeed';
}]);

/**
 * Disable Angular debugging based on Django DEBUG flag.
 */
SEED_app.config(['$compileProvider', function ($compileProvider) {
  $compileProvider.debugInfoEnabled(window.BE.debug);
}]);

/**
 * creates the object 'urls' which can be injected into a service, controller, etc.
 */
SEED_app.constant('urls', {
    search_buildings: BE.urls.search_buildings_url,
    search_building_snapshots: BE.urls.search_building_snapshots_url,
    save_match: BE.urls.save_match_url,
    seed_home: BE.urls.seed_home,
    update_building: BE.urls.update_building,
    static_url: BE.urls.STATIC_URL
});
SEED_app.constant('generated_urls', window.BE.app_urls);
