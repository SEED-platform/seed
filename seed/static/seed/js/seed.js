/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * AngularJS app 'config.seed' for SEED SPA
 */

angular.module('BE.seed.angular_dependencies', [
  'ngAnimate',
  'ngAria',
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
  'ui.grid.saveState',
  'ui.grid.selection',
  'ui.grid.treeView',
  'ui.router',
  'ui.router.stateHelper',
  'ui.sortable',
  'focus-if',
  'xeditable',
  angularDragula(angular),
  'pascalprecht.translate',
  'ngSanitize'
]);
angular.module('BE.seed.controllers', [
  'BE.seed.controller.about',
  'BE.seed.controller.accounts',
  'BE.seed.controller.admin',
  'BE.seed.controller.api',
  'BE.seed.controller.column_mappings',
  'BE.seed.controller.column_settings',
  'BE.seed.controller.create_sub_organization_modal',
  'BE.seed.controller.cycle_admin',
  'BE.seed.controller.data_quality_admin',
  'BE.seed.controller.data_quality_modal',
  'BE.seed.controller.data_quality_labels_modal',
  'BE.seed.controller.data_upload_modal',
  'BE.seed.controller.dataset',
  'BE.seed.controller.dataset_detail',
  'BE.seed.controller.delete_dataset_modal',
  'BE.seed.controller.delete_file_modal',
  'BE.seed.controller.delete_modal',
  'BE.seed.controller.developer',
  'BE.seed.controller.export_inventory_modal',
  'BE.seed.controller.geocode_modal',
  'BE.seed.controller.green_button_upload_modal',
  'BE.seed.controller.inventory_detail',
  'BE.seed.controller.inventory_detail_settings',
  'BE.seed.controller.inventory_detail_notes',
  'BE.seed.controller.inventory_detail_notes_modal',
  'BE.seed.controller.inventory_detail_meters',
  'BE.seed.controller.inventory_list',
  'BE.seed.controller.inventory_map',
  'BE.seed.controller.inventory_reports',
  'BE.seed.controller.inventory_settings',
  'BE.seed.controller.label_admin',
  'BE.seed.controller.mapping',
  'BE.seed.controller.members',
  'BE.seed.controller.menu',
  'BE.seed.controller.merge_modal',
  'BE.seed.controller.modified_modal',
  'BE.seed.controller.new_member_modal',
  'BE.seed.controller.organization',
  'BE.seed.controller.organization_settings',
  'BE.seed.controller.organization_sharing',
  'BE.seed.controller.pairing',
  'BE.seed.controller.pairing_settings',
  'BE.seed.controller.profile',
  'BE.seed.controller.rename_column_modal',
  'BE.seed.controller.security',
  'BE.seed.controller.settings_profile_modal',
  'BE.seed.controller.show_populated_columns_modal',
  'BE.seed.controller.ubid_modal',
  'BE.seed.controller.unmerge_modal',
  'BE.seed.controller.update_item_labels_modal'
]);
angular.module('BE.seed.filters', [
  'district',
  'fromNow',
  'ignoremap',
  'startFrom',
  'stripImportPrefix',
  'titleCase',
  'typedNumber'
]);
angular.module('BE.seed.directives', [
  'sdBasicPropertyInfoChart',
  'sdCheckCycleExists',
  'sdCheckLabelExists',
  'sdDropdown',
  'sdEnter',
  'sdLabel',
  'sdResizable',
  'sdScrollSync',
  'sdUploader'
]);
angular.module('BE.seed.services', [
  'BE.seed.service.auth',
  'BE.seed.service.data_quality',
  'BE.seed.service.column_mappings',
  'BE.seed.service.columns',
  'BE.seed.service.cycle',
  'BE.seed.service.dataset',
  'BE.seed.service.meter',
  'BE.seed.service.flippers',
  'BE.seed.service.geocode',
  'BE.seed.service.httpParamSerializerSeed',
  'BE.seed.service.inventory',
  'BE.seed.service.inventory_reports',
  'BE.seed.service.label',
  'BE.seed.service.main',
  'BE.seed.service.mapping',
  'BE.seed.service.matching',
  'BE.seed.service.meters',
  'BE.seed.service.modified',
  'BE.seed.service.note',
  'BE.seed.service.organization',
  'BE.seed.service.pairing',
  'BE.seed.service.search',
  'BE.seed.service.simple_modal',
  'BE.seed.service.ubid',
  'BE.seed.service.uploader',
  'BE.seed.service.user'
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
}]);

/**
 * Adds the Django CSRF token to all $http requests
 */
SEED_app.run([
  '$rootScope',
  '$cookies',
  '$http',
  '$log',
  '$q',
  '$state',
  '$transitions',
  '$translate',
  'editableOptions',
  'modified_service',
  'spinner_utility',
  function ($rootScope, $cookies, $http, $log, $q, $state, $transitions, $translate, editableOptions, modified_service, spinner_utility) {
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

    // ui-router transition actions
    $transitions.onStart({}, function (/*transition*/) {
      if (modified_service.isModified()) {
        return modified_service.showModifiedDialog().then(function () {
          modified_service.resetModified();
        }).catch(function () {
          return $q.reject('acknowledged modified');
        });
      } else {
        spinner_utility.show();
      }
    });

    $transitions.onSuccess({}, function (/*transition*/) {
      if ($rootScope.route_load_error && $rootScope.load_error_message === 'Your SEED account is not associated with any organizations. Please contact a SEED administrator.') {
        $state.go('home');
        return;
      }

      $rootScope.route_load_error = false;
      spinner_utility.hide();
    });

    $transitions.onError({}, function (transition) {
      spinner_utility.hide();
      if (transition.error().message === 'The transition was ignored') return;

      // route_load_error already set (User has no associated orgs)
      if ($rootScope.route_load_error && $rootScope.load_error_message === 'Your SEED account is not associated with any organizations. Please contact a SEED administrator.') {
        $state.go('home');
        return;
      }

      var error = transition.error().detail;

      if (error !== 'acknowledged modified') {
        $rootScope.route_load_error = true;

        var message;
        if (_.isString(_.get(error, 'data.message'))) message = _.get(error, 'data.message');
        else if (_.isString(_.get(error, 'data'))) message = _.get(error, 'data');

        if (error === 'not authorized' || error === 'Your page could not be located!') {
          $rootScope.load_error_message = $translate.instant(error);
        } else {
          $rootScope.load_error_message = '' || message || error;
        }
      }
    });

    $state.defaultErrorHandler(function (error) {
      $log.log(error);
    });

  }
]);

/**
 * Initialize release flippers
 */
// SEED_app.run([
//   'flippers',
//   function (flippers) {
//     // wraps some minor UI that we'll need until we migrate to delete the old
//     // PropertyState columns for EUI and area. This flipper should be removed
//     // for 2.4 when we remove the archived "_orig" area and EUI columns.
//     //
//     //
//     // flippers.make_flipper('ryan@ryanmccuaig.net', '2018-05-31T00:00:00Z',
//     //   'release:orig_columns', 'boolean', true);
//     //
//     // var make2 = _.partial(flippers.make_flipper, 'nicholas.long@nrel.gov', '2018-01-01T00:00:00Z');
//     // make2('release:bricr', 'boolean', true);
//   }
// ]);

/**
 * Create custom UI-Grid templates
 */
SEED_app.run([
  '$templateCache',
  function ($templateCache) {
    $templateCache.put('ui-grid/seedMergeHeader', '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : (!col.sort.direction ? \'none\' : \'other\'))}}"><div role="button" tabindex="0" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex" title="TOOLTIP"><span class="ui-grid-header-cell-label" ui-grid-one-bind-id-grid="col.uid + \'-header-text\'">{{ col.displayName CUSTOM_FILTERS }}</span> <span title="Merge Protection: Favor Existing" ui-grid-visible="col.colDef.merge_protection === \'Favor Existing\'" class="glyphicon glyphicon-lock lock"></span> <span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" ui-grid-visible="col.sort.direction" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-blank\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 )  : null}}" aria-hidden="true"></i> <sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div><div role="button" tabindex="0" ui-grid-one-bind-id-grid="col.uid + \'-menu-button\'" class="ui-grid-column-menu-button" ng-if="grid.options.enableColumnMenus && !col.isRowHeader  && col.colDef.enableColumnMenu !== false" ng-click="toggleMenu($event)" ng-class="{\'ui-grid-column-menu-button-last-col\': isLastCol}" ui-grid-one-bind-aria-label="i18n.headerCell.aria.columnMenuButtonLabel" aria-haspopup="true"><i class="ui-grid-icon-angle-down" aria-hidden="true">&nbsp;</i></div><div ui-grid-filter></div></div>');
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
          organizations_payload: ['auth_payload', 'organization_service', function (auth_payload, organization_service) {
            // Require auth_payload to successfully complete before attempting
            return organization_service.get_organizations();
          }],
          user_profile_payload: ['user_service', function (user_service) {
            return user_service.get_user_profile();
          }],
          users_payload: ['auth_payload', 'user_service', function (auth_payload, user_service) {
            // Require auth_payload to successfully complete before attempting
            return user_service.get_users();
          }]
        }
      })
      .state({
        name: 'reports',
        url: '/{inventory_type:properties|taxlots}/reports',
        templateUrl: static_url + 'seed/partials/inventory_reports.html',
        controller: 'inventory_reports_controller',
        resolve: {
          columns: ['$stateParams', 'user_service', 'inventory_service', 'naturalSort', function ($stateParams, user_service, inventory_service, naturalSort) {
            var organization_id = user_service.get_organization().id;
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns_for_org(organization_id).then(function (columns) {
                columns = _.reject(columns, 'related');
                columns = _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
                columns.sort(function (a, b) {
                  return naturalSort(a.displayName, b.displayName);
                });
                return columns;
              });
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlot_columns_for_org(organization_id).then(function (columns) {
                columns = _.reject(columns, 'related');
                columns = _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
                columns.sort(function (a, b) {
                  return naturalSort(a.displayName, b.displayName);
                });
                return columns;
              });
            }
          }],
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }],
          organization_payload: ['organization_service', 'user_service', function (organization_service, user_service) {
            var organization_id = user_service.get_organization().id;
            var organization = organization_service.get_organization(organization_id);
            return organization;
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
          profiles: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            var inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            return inventory_service.get_settings_profiles('List View Settings', inventory_type);
          }],
          current_profile: ['$stateParams', 'inventory_service', 'profiles', function ($stateParams, inventory_service, profiles) {
            var validProfileIds = _.map(profiles, 'id');
            var lastProfileId = inventory_service.get_last_profile($stateParams.inventory_type);
            if (_.includes(validProfileIds, lastProfileId)) {
              return _.find(profiles, {id: lastProfileId});
            }
            var currentProfile = _.first(profiles);
            if (currentProfile) inventory_service.save_last_profile(currentProfile.id, $stateParams.inventory_type);
            return currentProfile;
          }],
          shared_fields_payload: ['user_service', function (user_service) {
            return user_service.get_shared_buildings();
          }]
        }
      })
      .state({
        name: 'detail_settings',
        url: '/{inventory_type:properties|taxlots}/{view_id:int}/settings',
        templateUrl: static_url + 'seed/partials/inventory_detail_settings.html',
        controller: 'inventory_detail_settings_controller',
        resolve: {
          columns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns().then(function (columns) {
                _.remove(columns, 'related');
                _.remove(columns, {column_name: 'lot_number', table_name: 'PropertyState'});
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
          }],
          profiles: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            var inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            return inventory_service.get_settings_profiles('Detail View Settings', inventory_type);
          }],
          current_profile: ['$stateParams', 'inventory_service', 'profiles', function ($stateParams, inventory_service, profiles) {
            var validProfileIds = _.map(profiles, 'id');
            var lastProfileId = inventory_service.get_last_detail_profile($stateParams.inventory_type);
            if (_.includes(validProfileIds, lastProfileId)) {
              return _.find(profiles, {id: lastProfileId});
            }
            var currentProfile = _.first(profiles);
            if (currentProfile) inventory_service.save_last_detail_profile(currentProfile.id, $stateParams.inventory_type);
            return currentProfile;
          }]
        }
      })
      .state({
        name: 'inventory_detail_notes',
        url: '/{inventory_type:properties|taxlots}/{view_id:int}/notes',
        templateUrl: static_url + 'seed/partials/inventory_detail_notes.html',
        controller: 'inventory_detail_notes_controller',
        resolve: {
          inventory_payload: ['$state', '$stateParams', 'inventory_service', function ($state, $stateParams, inventory_service) {
            // load `get_building` before page is loaded to avoid page flicker.
            var view_id = $stateParams.view_id;
            var promise;
            if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property(view_id);
            else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot(view_id);
            promise.catch(function (err) {
              if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                // Inventory item not found for current organization, redirecting
                $state.go('inventory_list', {inventory_type: $stateParams.inventory_type});
              }
            });
            return promise;
          }],
          notes: ['$stateParams', 'note_service', 'user_service', function ($stateParams, note_service, user_service) {
            var organization_id = user_service.get_organization().id;
            return note_service.get_notes(organization_id, $stateParams.inventory_type, $stateParams.view_id);
          }]
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
            return mapping_service.get_column_mapping_suggestions(importfile_id);
          }],
          raw_columns_payload: ['mapping_service', '$stateParams', function (mapping_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return mapping_service.get_raw_columns(importfile_id);
          }],
          first_five_rows_payload: ['mapping_service', '$stateParams', function (mapping_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return mapping_service.get_first_five_rows(importfile_id);
          }],
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }],
          matching_criteria_columns_payload: ['organization_service', 'user_service', function (organization_service, user_service) {
            return organization_service.matching_criteria_columns(user_service.get_organization().id);
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
        name: 'pairing',
        url: '/data/pairing/{importfile_id:int}/{inventory_type:properties|taxlots}',
        templateUrl: static_url + 'seed/partials/pairing.html',
        controller: 'pairing_controller',
        resolve: {
          import_file_payload: ['dataset_service', '$stateParams', function (dataset_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return dataset_service.get_import_file(importfile_id);
          }],
          allPropertyColumns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            return inventory_service.get_property_columns().then(function (columns) {
              columns = _.reject(columns, 'related');
              return _.map(columns, function (col) {
                return _.omit(col, ['pinnedLeft', 'related']);
              });
            });
          }],
          allTaxlotColumns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            return inventory_service.get_taxlot_columns().then(function (columns) {
              columns = _.reject(columns, 'related');
              return _.map(columns, function (col) {
                return _.omit(col, ['pinnedLeft', 'related']);
              });
            });
          }],
          propertyInventory: ['inventory_service', function (inventory_service) {
            return inventory_service.get_properties(1, undefined, undefined, -1);
          }],
          taxlotInventory: ['inventory_service', function (inventory_service) {
            return inventory_service.get_taxlots(1, undefined, undefined, -1);
          }],
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }]
        }
      })
      .state({
        name: 'pairing_settings',
        url: '/data/pairing/{importfile_id:int}/{inventory_type:properties|taxlots}/settings',
        templateUrl: static_url + 'seed/partials/pairing_settings.html',
        controller: 'pairing_settings_controller',
        resolve: {
          import_file_payload: ['dataset_service', '$stateParams', function (dataset_service, $stateParams) {
            var importfile_id = $stateParams.importfile_id;
            return dataset_service.get_import_file(importfile_id);
          }],
          propertyColumns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            return inventory_service.get_property_columns().then(function (columns) {
              columns = _.reject(columns, 'related');
              return _.map(columns, function (col) {
                return _.omit(col, ['pinnedLeft', 'related']);
              });
            });
          }],
          taxlotColumns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            return inventory_service.get_taxlot_columns().then(function (columns) {
              columns = _.reject(columns, 'related');
              return _.map(columns, function (col) {
                return _.omit(col, ['pinnedLeft', 'related']);
              });
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
          dataset_payload: ['dataset_service', '$stateParams', '$state', '$q', 'spinner_utility', function (dataset_service, $stateParams, $state, $q, spinner_utility) {
            return dataset_service.get_dataset($stateParams.dataset_id)
              .catch(function (response) {
                if (response.status === 400 && response.data.message === 'Organization ID mismatch between dataset and organization') {
                  // Org id mismatch, likely due to switching organizations while viewing a dataset_detail page
                  _.delay(function () {
                    $state.go('dataset_list');
                    spinner_utility.hide();
                  });
                  // Resolve with empty response to avoid error alert
                  return $q.resolve({
                    status: 'success',
                    dataset: {}
                  });
                }
                return $q.reject(response);
              });
          }],
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
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
        templateUrl: static_url + 'seed/partials/organization_settings.html',
        controller: 'organization_settings_controller',
        resolve: {
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
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
        templateUrl: static_url + 'seed/partials/organization_sharing.html',
        controller: 'organization_sharing_controller',
        resolve: {
          all_columns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            var organization_id = $stateParams.organization_id;
            return inventory_service.get_used_columns(organization_id);
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
        name: 'organization_column_settings',
        url: '/accounts/{organization_id:int}/column_settings/{inventory_type:properties|taxlots}',
        templateUrl: static_url + 'seed/partials/column_settings.html',
        controller: 'column_settings_controller',
        resolve: {
          columns: ['$stateParams', 'inventory_service', 'naturalSort', function ($stateParams, inventory_service, naturalSort) {
            var organization_id = $stateParams.organization_id;

            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns_for_org(organization_id).then(function (columns) {
                columns = _.reject(columns, 'related');
                columns = _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
                columns.sort(function (a, b) {
                  return naturalSort(a.displayName, b.displayName);
                });
                return columns;
              });
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlot_columns_for_org(organization_id).then(function (columns) {
                columns = _.reject(columns, 'related');
                columns = _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
                columns.sort(function (a, b) {
                  return naturalSort(a.displayName, b.displayName);
                });
                return columns;
              });
            }
          }],
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
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
        name: 'organization_column_mappings',
        url: '/accounts/{organization_id:int}/column_mappings/{inventory_type:properties|taxlots}',
        templateUrl: static_url + 'seed/partials/column_mappings.html',
        controller: 'column_mappings_controller',
        resolve: {
          column_mappings: ['column_mappings_service', '$stateParams', 'naturalSort', function (column_mappings_service, $stateParams, naturalSort) {
            var organization_id = $stateParams.organization_id;

            return column_mappings_service.get_column_mappings_for_org(organization_id).then(function (data) {
              var propertyMappings = _.filter(data, function (datum) {
                return _.startsWith(datum.column_mapped.table_name, 'Property');
              });
              propertyMappings.sort(function (a, b) {
                return naturalSort(a.column_raw.column_name, b.column_raw.column_name);
              });
              var taxlotMappings = _.filter(data, function (datum) {
                return _.startsWith(datum.column_mapped.table_name, 'TaxLot');
              });
              taxlotMappings.sort(function (a, b) {
                return naturalSort(a.column_raw.column_name, b.column_raw.column_name);
              });

              if ($stateParams.inventory_type === 'properties') {
                return {
                  property_count: propertyMappings.length,
                  taxlot_count: taxlotMappings.length,
                  column_mappings: propertyMappings
                };
              } else if ($stateParams.inventory_type === 'taxlots') {
                return {
                  property_count: propertyMappings.length,
                  taxlot_count: taxlotMappings.length,
                  column_mappings: taxlotMappings
                };
              }
            });
          }],
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
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
        name: 'organization_data_quality',
        url: '/accounts/{organization_id:int}/data_quality/{inventory_type:properties|taxlots}',
        templateUrl: static_url + 'seed/partials/data_quality_admin.html',
        controller: 'data_quality_admin_controller',
        resolve: {
          columns: ['$stateParams', 'inventory_service', 'naturalSort', function ($stateParams, inventory_service, naturalSort) {
            var organization_id = $stateParams.organization_id;
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns_for_org(organization_id).then(function (columns) {
                columns = _.reject(columns, 'related');
                columns = _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
                columns.sort(function (a, b) {
                  return naturalSort(a.displayName, b.displayName);
                });
                return columns;
              });
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlot_columns_for_org(organization_id).then(function (columns) {
                columns = _.reject(columns, 'related');
                columns = _.map(columns, function (col) {
                  return _.omit(col, ['pinnedLeft', 'related']);
                });
                columns.sort(function (a, b) {
                  return naturalSort(a.displayName, b.displayName);
                });
                return columns;
              });
            }
          }],
          organization_payload: ['organization_service', '$stateParams', function (organization_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return organization_service.get_organization(organization_id);
          }],
          data_quality_rules_payload: ['data_quality_service', '$stateParams', function (data_quality_service, $stateParams) {
            var organization_id = $stateParams.organization_id;
            return data_quality_service.data_quality_rules(organization_id);
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
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }],
          profiles: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            var inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            return inventory_service.get_settings_profiles('List View Settings', inventory_type);
          }],
          current_profile: ['$stateParams', 'inventory_service', 'profiles', function ($stateParams, inventory_service, profiles) {
            var validProfileIds = _.map(profiles, 'id');
            var lastProfileId = inventory_service.get_last_profile($stateParams.inventory_type);
            if (_.includes(validProfileIds, lastProfileId)) {
              return _.find(profiles, {id: lastProfileId});
            }
            var currentProfile = _.first(profiles);
            if (currentProfile) inventory_service.save_last_profile(currentProfile.id, $stateParams.inventory_type);
            return currentProfile;
          }],
          labels: ['$stateParams', 'label_service', function ($stateParams, label_service) {
            return label_service.get_labels($stateParams.inventory_type).then(function (labels) {
              return _.filter(labels, function (label) {
                return !_.isEmpty(label.is_applied);
              });
            });
          }],
          all_columns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns();
            } else if ($stateParams.inventory_type === 'taxlots') {
              return inventory_service.get_taxlot_columns();
            }
          }]
        }
      })
      .state({
        name: 'inventory_map',
        url: '/{inventory_type:properties}/map',
        templateUrl: static_url + 'seed/partials/inventory_map.html',
        controller: 'inventory_map_controller',
        resolve: {
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }],
          labels: ['$stateParams', 'label_service', function ($stateParams, label_service) {
            return label_service.get_labels($stateParams.inventory_type).then(function (labels) {
              return _.filter(labels, function (label) {
                return !_.isEmpty(label.is_applied);
              });
            });
          }]
        }
      })
      .state({
        name: 'inventory_detail',
        url: '/{inventory_type:properties|taxlots}/{view_id:int}',
        templateUrl: static_url + 'seed/partials/inventory_detail.html',
        controller: 'inventory_detail_controller',
        resolve: {
          inventory_payload: ['$state', '$stateParams', 'inventory_service', function ($state, $stateParams, inventory_service) {
            // load `get_building` before page is loaded to avoid page flicker.
            var view_id = $stateParams.view_id;
            var promise;
            if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property(view_id);
            else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot(view_id);
            promise.catch(function (err) {
              if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                // Inventory item not found for current organization, redirecting
                $state.go('inventory_list', {inventory_type: $stateParams.inventory_type});
              }
            });
            return promise;
          }],
          columns: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            if ($stateParams.inventory_type === 'properties') {
              return inventory_service.get_property_columns().then(function (columns) {
                _.remove(columns, 'related');
                _.remove(columns, {column_name: 'lot_number', table_name: 'PropertyState'});
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
          }],
          profiles: ['$stateParams', 'inventory_service', function ($stateParams, inventory_service) {
            var inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            return inventory_service.get_settings_profiles('Detail View Settings', inventory_type);
          }],
          current_profile: ['$stateParams', 'inventory_service', 'profiles', function ($stateParams, inventory_service, profiles) {
            var validProfileIds = _.map(profiles, 'id');
            var lastProfileId = inventory_service.get_last_detail_profile($stateParams.inventory_type);
            if (_.includes(validProfileIds, lastProfileId)) {
              return _.find(profiles, {id: lastProfileId});
            }
            var currentProfile = _.first(profiles);
            if (currentProfile) inventory_service.save_last_detail_profile(currentProfile.id, $stateParams.inventory_type);
            return currentProfile;
          }],
          labels_payload: ['$stateParams', 'inventory_payload', 'label_service', function ($stateParams, inventory_payload, label_service) {
            return label_service.get_labels($stateParams.inventory_type, [$stateParams.view_id]);
          }]
        }
      })
      .state({
        name: 'inventory_detail_meters',
        url: '/{inventory_type:properties|taxlots}/{view_id:int}/meters',
        templateUrl: static_url + 'seed/partials/inventory_detail_meters.html',
        controller: 'inventory_detail_meters_controller',
        resolve: {
          inventory_payload: ['$state', '$stateParams', 'inventory_service', function ($state, $stateParams, inventory_service) {
            // load `get_building` before page is loaded to avoid page flicker.
            var view_id = $stateParams.view_id;
            var promise = inventory_service.get_property(view_id);
            promise.catch(function (err) {
              if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                // Inventory item not found for current organization, redirecting
                $state.go('inventory_list', {inventory_type: $stateParams.inventory_type});
              }
            });
            return promise;
          }],
          property_meter_usage: ['$stateParams', 'user_service', 'meter_service', function ($stateParams, user_service, meter_service) {
            var organization_id = user_service.get_organization().id;
            return meter_service.property_meter_usage($stateParams.view_id, organization_id, 'Exact');
          }],
          meters: ['$stateParams', 'user_service', 'meter_service', function ($stateParams, user_service, meter_service) {
            var organization_id = user_service.get_organization().id;
            return meter_service.get_meters($stateParams.view_id, organization_id);
          }],
          cycles: ['cycle_service', function (cycle_service) {
            return cycle_service.get_cycles();
          }]
        }
      });
  }]);

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

SEED_app.config(['$translateProvider', function ($translateProvider) {
  $translateProvider
    .useStaticFilesLoader({
      prefix: '/static/seed/locales/',
      suffix: '.json'
    })
    .registerAvailableLanguageKeys(['en_US', 'fr_CA'], {
      en: 'en_US',
      fr: 'fr_CA',
      'en_*': 'en_US',
      'fr_*': 'fr_CA',
      '*': 'en_US'
    })
    // allow some HTML in the translation strings,
    // see https://angular-translate.github.io/docs/#/guide/19_security
    .useSanitizeValueStrategy('escapeParameters')
    // interpolation for plurals
    .useMessageFormatInterpolation();

  $translateProvider.determinePreferredLanguage();
  moment.locale($translateProvider.preferredLanguage());

}]);


/**
 * creates the object 'urls' which can be injected into a service, controller, etc.
 */
SEED_app.constant('urls', {
  seed_home: BE.urls.seed_home,
  static_url: BE.urls.STATIC_URL
});
SEED_app.constant('generated_urls', window.BE.app_urls);

SEED_app.constant('naturalSort', function (a, b) {
  /**
   * Natural Sort algorithm for Javascript - Version 0.8.1 - Released under MIT license
   * Author: Jim Palmer (based on chunking idea from Dave Koelle)
   */
  var re = /(^([+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?(?=\D|\s|$))|^0x[\da-fA-F]+$|\d+)/g,
    sre = /^\s+|\s+$/g, // trim pre-post whitespace
    snre = /\s+/g, // normalize all whitespace to single ' ' character
    dre = /(^([\w ]+,?[\w ]+)?[\w ]+,?[\w ]+\d+:\d+(:\d+)?[\w ]?|^\d{1,4}[/-]\d{1,4}[/-]\d{1,4}|^\w+, \w+ \d+, \d{4})/,
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
    if (/[^\x00-\x80]/.test(oFxNcL + oFyNcL) && oFxNcL.localeCompare) { // eslint-disable-line no-control-regex
      var comp = oFxNcL.localeCompare(oFyNcL);
      return comp / Math.abs(comp);
    }
    if (oFxNcL < oFyNcL) return -1;
    else if (oFxNcL > oFyNcL) return 1;
  }
});
