/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * AngularJS app 'config.seed' for SEED SPA
 */

angular.module('BE.seed.angular_dependencies', [
  'ngCookies'
]);
angular.module('BE.seed.vendor_dependencies', [
  'ngTagsInput',
  'ui-notification',
  'ui.bootstrap',
  'ui.grid',
  'ui.grid.draggable-rows',
  'ui.grid.exporter',
  'ui.grid.moveColumns',
  'ui.grid.pinning',
  'ui.grid.resizeColumns',
  'ui.grid.selection',
  'ui.grid.treeView',
  'ui.router',
  'ui.router.stateHelper',
  'ui.sortable',
  'ui.tree',
  'xeditable'
]);
angular.module('BE.seed.controllers', [
  'BE.seed.controller.about',
  'BE.seed.controller.accounts',
  'BE.seed.controller.admin',
  'BE.seed.controller.api',
  'BE.seed.controller.building_list',
  'BE.seed.controller.buildings_settings',
  'BE.seed.controller.cleansing',
  'BE.seed.controller.cleansing_admin',
  'BE.seed.controller.cycle_admin',
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
  'BE.seed.controller.export_inventory_modal',
  'BE.seed.controller.export_modal',
  'BE.seed.controller.inventory_detail',
  'BE.seed.controller.inventory_detail_settings',
  'BE.seed.controller.inventory_list',
  'BE.seed.controller.inventory_reports',
  'BE.seed.controller.inventory_settings',
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
  'BE.seed.controller.security',
  'BE.seed.controller.update_item_labels_modal'
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
  'sdBasicBuildingInfoChart',
  'sdBasicPropertyInfoChart',
  'sdCheckCycleExists',
  'sdCheckLabelExists',
  'sdDropdown',
  'sdEnter',
  'sdLabel',
  'sdResizable',
  'sdUploader'
]);
angular.module('BE.seed.services', [
  'BE.seed.service.audit',
  'BE.seed.service.auth',
  'BE.seed.service.building',
  'BE.seed.service.cleansing',
  'BE.seed.service.cycle',
  'BE.seed.service.dataset',
  'BE.seed.service.export',
  'BE.seed.service.httpParamSerializerSeed',
  'BE.seed.service.inventory',
  'BE.seed.service.inventory_reports',
  'BE.seed.service.label',
  'BE.seed.service.main',
  'BE.seed.service.mapping',
  'BE.seed.service.matching',
  'BE.seed.service.organization',
  'BE.seed.service.project',
  'BE.seed.service.search',
  'BE.seed.service.simple_modal',
  'BE.seed.service.uploader',
  'BE.seed.service.user',
  'mappingValidatorService'
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
  ], ['$interpolateProvider', '$qProvider', function ($interpolateProvider, $qProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
    $qProvider.errorOnUnhandledRejections(false);
  }]
);

/**
 * Adds the Django CSRF token to all $http requests
 */
SEED_app.run([
  '$http',
  '$cookies',
  '$rootScope',
  'editableOptions',
  function ($http, $cookies, $rootScope, editableOptions) {
    var csrftoken = $cookies.get('csrftoken');
    BE.csrftoken = csrftoken;
    $http.defaults.headers.common['X-CSRFToken'] = csrftoken;
    $http.defaults.headers.post['X-CSRFToken'] = csrftoken;
    $http.defaults.xsrfCookieName = 'csrftoken';
    $http.defaults.xsrfHeaderName = 'X-CSRFToken';

    //config ANGULAR-XEDITABLE ... (this is the recommended place rather than in .config)...
    editableOptions.theme = 'bs3';

    // Use lodash in views
    $rootScope._ = window._;
  }
]);

/**
 * url routing declaration for SEED
 */
SEED_app.config(['stateHelperProvider', '$urlRouterProvider', '$locationProvider',
  function (stateHelperProvider, $urlRouterProvider, $locationProvider) {

    var static_url = BE.urls.STATIC_URL;

    $locationProvider.hashPrefix('');
    $urlRouterProvider.otherwise('/');

    stateHelperProvider
      .state({
        name: 'home',
        url: '/',
        templateUrl: static_url + 'seed/partials/home.html'
      })
      .state({
        name: 'profile',
        url: '/profile',
        templateUrl: static_url + 'seed/partials/profile.html',
        controller: 'profile_controller',
        resolve: {
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_superuser']);
          }],
          user_profile_payload: ['user_service', function (user_service) {
            return user_service.get_user_profile();
          }]
        }
      })
      .state({
        name: 'security',
        url: '/profile/security',
        templateUrl: static_url + 'seed/partials/security.html',
        controller: 'security_controller',
        resolve: {
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_superuser']);
          }],
          user_profile_payload: ['user_service', function (user_service) {
            return user_service.get_user_profile();
          }]
        }
      })
      .state({
        name: 'developer',
        url: '/profile/developer',
        templateUrl: static_url + 'seed/partials/developer.html',
        controller: 'developer_controller',
        resolve: {
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_superuser']);
          }],
          user_profile_payload: ['user_service', function (user_service) {
            return user_service.get_user_profile();
          }]
        }
      })
      .state({
        name: 'admin',
        url: '/profile/admin',
        templateUrl: static_url + 'seed/partials/admin.html',
        controller: 'admin_controller',
        resolve: {
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_superuser'])
              .then(function (data) {
                if (data.auth.requires_superuser) {
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
      /*.state({
       name: 'projects',
       url: '/projects',
       templateUrl: static_url + 'seed/partials/projects.html',
       controller: 'project_list_controller',
       resolve: {
       projects_payload: ['project_service', function (project_service) {
       return project_service.get_projects();
       }]
       }
       })
       .state({
       name: 'project_detail',
       url: '/projects/{project_id:int}',
       templateUrl: static_url + 'seed/partials/project_detail.html',
       controller: 'building_list_controller',
       resolve: {
       search_payload: ['building_services', '$state', '$stateParams', function (building_services, $state, $stateParams) {
       var orderBy = '';
       var sortReverse = false;
       var params = angular.copy($stateParams);
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
       var prefix = _.replace($state.current.url, ':project_id', project_slug);
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
       default_columns: ['user_service', function (user_service) {
       return user_service.get_default_columns();
       }],
       all_columns: ['building_services', '$stateParams', function (building_services, $stateParams) {
       var params = angular.copy($stateParams);
       var project_slug = params.project_id;
       return building_services.get_columns();
       }],
       project_payload: ['$stateParams', 'project_service', function ($stateParams, project_service) {
       var params = angular.copy($stateParams);
       var project_slug = params.project_id;
       return project_service.get_project(project_slug);
       }]
       }
       })
       .state({
       name: 'project_settings',
       url: '/projects/{project_id:int}/settings',
       templateUrl: static_url + 'seed/partials/project_settings.html',
       controller: 'buildings_settings_controller',
       resolve: {
       all_columns: ['building_services', function (building_services) {
       return building_services.get_columns();
       }],
       default_columns: ['user_service', function (user_service) {
       return user_service.get_default_columns();
       }],
       shared_fields_payload: ['user_service', function (user_service) {
       return user_service.get_shared_buildings();
       }],
       $uibModalInstance: function () {
       return {close: function () {}};
       },
       project_payload: ['$stateParams', 'project_service', function ($stateParams, project_service) {
       var params = angular.copy($stateParams);
       var project_slug = params.project_id;
       return project_service.get_project(project_slug);
       }],
       building_payload: function () {
       return {building: {}};
       }
       }
       })
       .state({
       name: 'building_detail_section',
       url: '/projects/{project_id:int}/{building_id:int}',
       templateUrl: static_url + 'seed/partials/building_detail_section.html',
       controller: 'building_detail_controller',
       resolve: {
       building_payload: ['building_services', '$stateParams', function (building_services, $stateParams) {
       var building_id = $stateParams.building_id;
       return building_services.get_building(building_id);
       }],
       all_columns: ['building_services', function (building_services) {
       return building_services.get_columns();
       }],
       audit_payload: function () {
       return {audit_logs: {}};
       },
       default_columns: ['user_service', function (user_service) {
       return user_service.get_default_building_detail_columns();
       }]
       }
       })*/
      .state({
        name: 'buildings',
        url: '/buildings',
        templateUrl: static_url + 'seed/partials/buildings.html',
        controller: 'building_list_controller',
        resolve: {
          search_payload: ['building_services', '$state', '$stateParams', function (building_services, $state, $stateParams) {
            // Defaults

            var q = $stateParams.q || '';
            var orderBy = '';
            var sortReverse = false;
            var params = {};
            var numberPerPage = 10;
            var pageNumber = 1;

            // Check session storage for order, sort, and filter values.
            if (!_.isUndefined(Storage)) {

              var prefix = $state.current.url;

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
          default_columns: ['user_service', function (user_service) {
            return user_service.get_default_columns();
          }],
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          project_payload: function () {
            return {
              project: {}
            };
          }
        }
      })
      .state({
        name: 'buildings_settings',
        url: '/buildings/settings',
        templateUrl: static_url + 'seed/partials/buildings_settings.html',
        controller: 'buildings_settings_controller',
        resolve: {
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          default_columns: ['user_service', function (user_service) {
            return user_service.get_default_columns();
          }],
          shared_fields_payload: ['user_service', function (user_service) {
            return user_service.get_shared_buildings();
          }],
          $uibModalInstance: function () {
            return {
              close: function () {
              }
            };
          },
          project_payload: function () {
            return {project: {}};
          },
          building_payload: function () {
            return {building: {}};
          }
        }
      })
      .state({
        name: 'reports',
        url: '/{inventory_type:properties|taxlots}/reports',
        templateUrl: static_url + 'seed/partials/inventory_reports.html',
        controller: 'inventory_reports_controller',
        resolve: {
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }]
        }
      })
      .state({
        name: 'list_settings',
        url: '/{inventory_type:properties|taxlots}/settings',
        templateUrl: static_url + 'seed/partials/inventory_settings.html',
        controller: 'inventory_settings_controller',
        resolve: {
          $uibModalInstance: function () {
            return {
              close: function () {
              }
            };
          },
          all_columns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns();
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlot_columns();
            }
          }],
          shared_fields_payload: ['user_service', function (user_service) {
            return user_service.get_shared_buildings();
          }]
        }
      })
      .state({
        name: 'detail_settings',
        url: '/{inventory_type:properties|taxlots}/{inventory_id:int}/cycles/{cycle_id:int}/settings',
        templateUrl: static_url + 'seed/partials/inventory_detail_settings.html',
        controller: 'inventory_detail_settings_controller',
        resolve: {
          $uibModalInstance: function () {
            return {
              close: function () {
              }
            };
          },
          columns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns().then(function (columns) {
                _.remove(columns, 'related');
                return _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
              });
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlot_columns().then(function (columns) {
                _.remove(columns, 'related');
                return _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
              });
            }
          }]
        }
      })
      .state({
        name: 'building_detail',
        url: '/buildings/{building_id:int}',
        templateUrl: static_url + 'seed/partials/building_detail_section.html',
        controller: 'building_detail_controller',
        resolve: {
          building_payload: ['building_services', '$stateParams', function (building_services, $stateParams) {
            // load `get_building` before page is loaded to avoid
            // page flicker.
            var building_id = $stateParams.building_id;
            return building_services.get_building(building_id);
          }],
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          audit_payload: function () {
            return {audit_logs: {}};
          },
          default_columns: ['user_service', function (user_service) {
            return user_service.get_default_building_detail_columns();
          }]
        }
      })
      .state({
        name: 'building_projects',
        url: '/buildings/{building_id:int}/projects',
        templateUrl: static_url + 'seed/partials/building_projects_section.html',
        controller: 'building_detail_controller',
        resolve: {
          building_payload: ['building_services', '$stateParams', function (building_services, $stateParams) {
            // load `get_building` before page is loaded to avoid
            // page flicker.
            var building_id = $stateParams.building_id;
            return building_services.get_building(building_id);
          }],
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          audit_payload: function () {
            return {audit_logs: {}};
          },
          default_columns: function () {
            return {columns: {}};
          }
        }
      })
      .state({
        name: 'building_audit_log',
        url: '/buildings/{building_id:int}/audit',
        templateUrl: static_url + 'seed/partials/building_audit_log.html',
        controller: 'building_detail_controller',
        resolve: {
          building_payload: ['building_services', '$stateParams', function (building_services, $stateParams) {
            // load `get_building` before page is loaded to avoid
            // page flicker.
            var building_id = $stateParams.building_id;
            return building_services.get_building(building_id);
          }],
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          audit_payload: ['audit_service', '$stateParams', function (audit_service, $stateParams) {
            var building_id = $stateParams.building_id;
            return audit_service.get_building_logs(building_id);
          }],
          default_columns: function () {
            return {columns: {}};
          }
        }
      })
      .state({
        name: 'building_energy',
        url: '/buildings/{building_id:int}/energy',
        templateUrl: static_url + 'seed/partials/building_energy_section.html',
        controller: 'building_detail_controller',
        resolve: {
          building_payload: ['building_services', '$stateParams', function (building_services, $stateParams) {
            // load `get_building` before page is loaded to avoid
            // page flicker.
            var building_id = $stateParams.building_id;
            return building_services.get_building(building_id);
          }],
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          audit_payload: function () {
            return {audit_logs: {}};
          },
          default_columns: function () {
            return {columns: {}};
          }
        }
      })
      .state({
        name: 'building_settings',
        url: '/buildings/{building_id:int}/settings',
        templateUrl: static_url + 'seed/partials/building_settings_section.html',
        controller: 'buildings_settings_controller',
        resolve: {
          building_payload: ['building_services', '$stateParams', function (building_services, $stateParams) {
            // load `get_building` before page is loaded to avoid
            // page flicker.
            var building_id = $stateParams.building_id;
            return building_services.get_building(building_id);
          }],
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          default_columns: ['user_service', function (user_service) {
            return user_service.get_default_building_detail_columns();
          }],
          shared_fields_payload: function () {
            return {show_shared_buildings: false};
          },
          $uibModalInstance: function () {
            return {
              close: function () {
              }
            };
          },
          project_payload: function () {
            return {project: {}};
          }
        }
      })
      .state({
        name: 'mapping',
        url: '/data/mapping/{importfile_id:int}',
        templateUrl: static_url + 'seed/partials/mapping.html',
        controller: 'mapping_controller',
        resolve: {
          import_file_payload: ['dataset_service', '$stateParams', function (dataset_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return dataset_service.get_import_file(importfile_id);
          }],
          suggested_mappings_payload: ['mapping_service', '$stateParams', function (mapping_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return mapping_service.get_column_mapping_suggestions(
              importfile_id
            );
          }],
          raw_columns_payload: ['mapping_service', '$stateParams', function (mapping_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return mapping_service.get_raw_columns(
              importfile_id
            );
          }],
          first_five_rows_payload: ['mapping_service', '$stateParams', function (mapping_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return mapping_service.get_first_five_rows(
              importfile_id
            );
          }],
          property_columns: ['inventory_service', function (inventory_service) {
            return inventory_service.get_property_columns();
          }],
          taxlot_columns: ['inventory_service', function (inventory_service) {
            return inventory_service.get_taxlot_columns();
          }],
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_member'])
              .then(function (data) {
                if (data.auth.requires_member) {
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
      .state({
        name: 'matching',
        url: '/data/matching/{importfile_id:int}',
        templateUrl: static_url + 'seed/partials/matching.html',
        controller: 'matching_controller',
        resolve: {
          import_file_payload: ['dataset_service', '$stateParams', function (dataset_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return dataset_service.get_import_file(importfile_id);
          }],
          buildings_payload: ['building_services', '$stateParams', function (building_services, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return building_services.search_matching_buildings(
              '', 10, 1, '', false, {}, importfile_id);
          }],
          default_columns: ['user_service', function (user_service) {
            return user_service.get_default_columns();
          }],
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_member'])
              .then(function (data) {
                if (data.auth.requires_member) {
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
      .state({
        name: 'dataset_list',
        url: '/data',
        templateUrl: static_url + 'seed/partials/dataset_list.html',
        controller: 'dataset_list_controller',
        resolve: {
          datasets_payload: ['dataset_service', function (dataset_service) {
            return dataset_service.get_datasets();
          }],
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_member'])
              .then(function (data) {
                if (data.auth.requires_member) {
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
      .state({
        name: 'dataset_detail',
        url: '/data/{dataset_id:int}',
        templateUrl: static_url + 'seed/partials/dataset_detail.html',
        controller: 'dataset_detail_controller',
        resolve: {
          dataset_payload: ['dataset_service', '$stateParams', function (dataset_service, $stateParams) {
            var dataset_id = $stateParams.dataset_id;
            return dataset_service.get_dataset(dataset_id);
          }],
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_member'])
              .then(function (data) {
                if (data.auth.requires_member) {
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
      .state({
        name: 'contact',
        url: '/contact',
        templateUrl: static_url + 'seed/partials/contact.html'
      })
      .state({
        name: 'api_docs',
        url: '/api/swagger',
        templateUrl: static_url + 'seed/partials/api_docs.html',
        controller: 'api_controller'
      })
      .state({
        name: 'about',
        url: '/about',
        templateUrl: static_url + 'seed/partials/about.html',
        controller: 'about_controller',
        resolve: {
          version_payload: ['main_service', function (main_service) {
            return main_service.version();
          }]
        }
      })
      .state({
        name: 'organizations',
        url: '/accounts',
        templateUrl: static_url + 'seed/partials/accounts.html',
        controller: 'accounts_controller',
        resolve: {
          organization_payload: ['organization_service', function (organization_service) {
            return organization_service.get_organizations();
          }]
        }
      })
      .state({
        name: 'organization_settings',
        url: '/accounts/{organization_id:int}',
        templateUrl: static_url + 'seed/partials/settings.html',
        controller: 'organization_settings_controller',
        resolve: {
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns(true);
          }],
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
          }],
          query_threshold_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_query_threshold(organization_id);
          }],
          shared_fields_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_shared_fields(organization_id);
          }],
          auth_payload: ['auth_service', '$stateParams', '$q', function (auth_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return auth_service.is_authorized(organization_id, ['requires_owner'])
              .then(function (data) {
                if (data.auth.requires_owner) {
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
      .state({
        name: 'organization_sharing',
        url: '/accounts/{organization_id:int}/sharing',
        templateUrl: static_url + 'seed/partials/sharing.html',
        controller: 'organization_settings_controller',
        resolve: {
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
          }],
          query_threshold_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_query_threshold(organization_id);
          }],
          shared_fields_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_shared_fields(organization_id);
          }],
          auth_payload: ['auth_service', '$stateParams', '$q', function (auth_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return auth_service.is_authorized(organization_id, ['requires_owner'])
              .then(function (data) {
                if (data.auth.requires_owner) {
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
      .state({
        name: 'organization_cleansing',
        url: '/accounts/{organization_id:int}/data_cleansing',
        templateUrl: static_url + 'seed/partials/cleansing_admin.html',
        controller: 'cleansing_admin_controller',
        resolve: {
          all_columns: ['building_services', function (building_services) {
            return building_services.get_columns();
          }],
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
          }],
          cleansing_rules_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_cleansing_rules(organization_id);
          }],
          auth_payload: ['auth_service', '$stateParams', '$q', function (auth_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return auth_service.is_authorized(organization_id, ['requires_owner'])
              .then(function (data) {
                if (data.auth.requires_owner) {
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
      .state({
        name: 'organization_cycles',
        url: '/accounts/{organization_id:int}/cycles',
        templateUrl: static_url + 'seed/partials/cycle_admin.html',
        controller: 'cycle_admin_controller',
        resolve: {
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            return organization_service.get_organization($stateParams.organization_id);
          }],
          cycles_payload: ['cycle_service', '$stateParams', function (cycle_service, $stateParams) {
            return cycle_service.get_cycles_for_org($stateParams.organization_id);
          }],
          auth_payload: ['auth_service', '$stateParams', '$q', function (auth_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return auth_service.is_authorized(organization_id, ['requires_owner'])
              .then(function (data) {
                if (data.auth.requires_owner) {
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
      .state({
        name: 'organization_labels',
        url: '/accounts/{organization_id:int}/labels',
        templateUrl: static_url + 'seed/partials/label_admin.html',
        controller: 'label_admin_controller',
        resolve: {
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
          }],
          labels_payload: ['label_service', '$stateParams', function (label_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return label_service.get_labels_for_org(organization_id);
          }],
          auth_payload: ['auth_service', '$stateParams', '$q', function (auth_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return auth_service.is_authorized(organization_id, ['requires_owner'])
              .then(function (data) {
                if (data.auth.requires_owner) {
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
      .state({
        name: 'organization_sub_orgs',
        url: '/accounts/{organization_id:int}/sub_org',
        templateUrl: static_url + 'seed/partials/sub_org.html',
        controller: 'organization_controller',
        resolve: {
          users_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization_users({org_id: organization_id});
          }],
          organization_payload: ['organization_service', '$stateParams', '$q', function (organization_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id)
              .then(function (data) {
                if (data.organization.is_parent) {
                  return data;
                } else {
                  return $q.reject('Your page could not be located!');
                }
              });
          }],
          auth_payload: ['auth_service', '$stateParams', '$q', function (auth_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return auth_service.is_authorized(organization_id, ['requires_owner'])
              .then(function (data) {
                if (data.auth.requires_owner) {
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
      .state({
        name: 'organization_members',
        url: '/accounts/{organization_id:int}/members',
        templateUrl: static_url + 'seed/partials/members.html',
        controller: 'members_controller',
        resolve: {
          users_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization_users({org_id: organization_id});
          }],
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
          }],
          auth_payload: ['auth_service', '$stateParams', '$q', function (auth_service, $stateParams, $q) {
            var organization_id = $stateParams.organization_id;
            return auth_service.is_authorized(organization_id, ['can_invite_member', 'can_remove_member', 'requires_owner', 'requires_member'])
              .then(function (data) {
                if (data.auth.requires_member) {
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
      .state({
        name: 'inventory_list',
        url: '/{inventory_type:properties|taxlots}',
        templateUrl: static_url + 'seed/partials/inventory_list.html',
        controller: 'inventory_list_controller',
        resolve: {
          inventory: ['$stateParams', 'inventory_service', 'columns', function ($stateParams, inventory_service, columns) {
            // inventory: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            var localStorageKey = 'grid.' + $stateParams.inventory_type;
            var myColumns = inventory_service.loadSettings(localStorageKey, columns);
            var visibleColumns = _.map(_.filter(myColumns, 'visible'), 'name');
            // console.log('before: ', visibleColumns);
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_properties(1, undefined, undefined, visibleColumns).then(function (inv) {
                // return inventory_service.get_properties(1).then(function (inv) {
                return _.extend({'columns': myColumns}, inv);
              });
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlots(1, undefined, undefined, visibleColumns).then(function (inv) {
                return _.extend({'columns': myColumns}, inv);
              });
            }
          }],
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }],
          labels: ['$stateParams', 'label_service', function ($stateParams, label_service) {
            return label_service.get_labels([], {
              inventory_type: $stateParams.inventory_type
            }).then(function (labels) {
              return _.filter(labels, function (label) {
                return !_.isEmpty(label.is_applied);
              });
            });
          }],
          columns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns();
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlot_columns();
            }
          }]
        }
      })
      .state({
        name: 'inventory_detail',
        url: '/{inventory_type:properties|taxlots}/{inventory_id:int}/cycles/{cycle_id:int}',
        templateUrl: static_url + 'seed/partials/inventory_detail.html',
        controller: 'inventory_detail_controller',
        resolve: {
          inventory_payload: ['$state', '$stateParams', 'inventory_service', function ($state, $stateParams, inventory_service) {
            // load `get_building` before page is loaded to avoid page flicker.
            var inventory_id = $stateParams.inventory_id;
            var cycle_id = $stateParams.cycle_id;
            var promise;
            if ($stateParams.inventory_type == 'properties') promise = inventory_service.get_property(inventory_id, cycle_id);
            else if ($stateParams.inventory_type == 'taxlots') promise = inventory_service.get_taxlot(inventory_id, cycle_id);
            promise.catch(function (err) {
              if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                // Inventory item not found for current organization, redirecting
                $state.go('inventory_list', {inventory_type: $stateParams.inventory_type});
              }
            });
            return promise;
          }],
          columns: ['inventory_service', '$stateParams', function (inventory_service, $stateParams) {
            if ($stateParams.inventory_type == 'properties') {
              return inventory_service.get_property_columns().then(function (columns) {
                _.remove(columns, 'related');
                return _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
              });
            } else if ($stateParams.inventory_type == 'taxlots') {
              return inventory_service.get_taxlot_columns().then(function (columns) {
                _.remove(columns, 'related');
                return _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
              });
            }
          }],
          labels_payload: ['$stateParams', 'label_service', function ($stateParams, label_service) {
            return label_service.get_labels([$stateParams.inventory_id], {
              inventory_type: $stateParams.inventory_type
            });
          }]
        }
      });
  }]);

/**
 * whitelist needed to load html partials from Amazon AWS S3
 * defaults to 'self' otherwise
 */
SEED_app.config([
  '$sceDelegateProvider',
  function ($sceDelegateProvider) {
    $sceDelegateProvider.resourceUrlWhitelist([
      'self',
      '**'
    ]);
  }
]);

SEED_app.config(['$httpProvider', function ($httpProvider) {
  $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
  $httpProvider.defaults.paramSerializer = 'httpParamSerializerSeed';
}]);

/**
 * Disable Angular debugging based on Django DEBUG flag.
 */
SEED_app.config(['$compileProvider', function ($compileProvider) {
  $compileProvider.debugInfoEnabled(window.BE.debug);
  $compileProvider.commentDirectivesEnabled(false);
  // $compileProvider.cssClassDirectivesEnabled(false); // This cannot be enabled due to the draggable ui-grid rows
}]);

/**
 * creates the object 'urls' which can be injected into a service, controller, etc.
 */
SEED_app.constant('urls', {
  search_buildings: BE.urls.search_buildings_url,
  save_match: BE.urls.save_match_url,
  seed_home: BE.urls.seed_home,
  // update_building: BE.urls.update_building,
  static_url: BE.urls.STATIC_URL
});
SEED_app.constant('generated_urls', window.BE.app_urls);

SEED_app.constant('naturalSort', function (a, b) {
  /*
   * Natural Sort algorithm for Javascript - Version 0.8.1 - Released under MIT license
   * Author: Jim Palmer (based on chunking idea from Dave Koelle)
   */
  var re = /(^([+\-]?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?(?=\D|\s|$))|^0x[\da-fA-F]+$|\d+)/g,
    sre = /^\s+|\s+$/g, // trim pre-post whitespace
    snre = /\s+/g, // normalize all whitespace to single ' ' character
    dre = /(^([\w ]+,?[\w ]+)?[\w ]+,?[\w ]+\d+:\d+(:\d+)?[\w ]?|^\d{1,4}[\/\-]\d{1,4}[\/\-]\d{1,4}|^\w+, \w+ \d+, \d{4})/,
    ore = /^0/,
    i = function (s) {
      return (('' + s).toLowerCase() || '' + s).replace(sre, '');
    },
    // convert all to strings strip whitespace
    x = i(a),
    y = i(b),
    // chunk/tokenize
    xN = x.replace(re, '\0$1\0').replace(/\0$/, '').replace(/^\0/, '').split('\0'),
    yN = y.replace(re, '\0$1\0').replace(/\0$/, '').replace(/^\0/, '').split('\0'),
    // numeric or date detection
    xD = xN.length !== 1 && Date.parse(x),
    yD = xD && y.match(dre) && Date.parse(y) || null,
    normChunk = function (s, l) {
      // normalize spaces; find floats not starting with '0', string or 0 if not defined (Clint Priest)
      return (!s.match(ore) || l == 1) && parseFloat(s) || s.replace(snre, ' ').replace(sre, '') || 0;
    },
    oFxNcL, oFyNcL;
  // first try and sort Dates
  if (yD) {
    if (xD < yD) return -1;
    else if (xD > yD) return 1;
  }
  // natural sorting through split numeric strings and default strings
  for (var cLoc = 0, xNl = xN.length, yNl = yN.length, numS = Math.max(xNl, yNl); cLoc < numS; cLoc++) {
    oFxNcL = normChunk(xN[cLoc] || '', xNl);
    oFyNcL = normChunk(yN[cLoc] || '', yNl);
    // handle numeric vs string comparison - number < string - (Kyle Adams)
    if (isNaN(oFxNcL) !== isNaN(oFyNcL)) {
      return isNaN(oFxNcL) ? 1 : -1;
    }
    // if unicode use locale comparison
    if (/[^\x00-\x80]/.test(oFxNcL + oFyNcL) && oFxNcL.localeCompare) {
      var comp = oFxNcL.localeCompare(oFyNcL);
      return comp / Math.abs(comp);
    }
    if (oFxNcL < oFyNcL) return -1;
    else if (oFxNcL > oFyNcL) return 1;
  }
});
