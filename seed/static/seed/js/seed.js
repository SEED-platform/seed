/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * AngularJS app 'config.seed' for SEED SPA
 */
(() => {
  angular.module('SEED.angular_dependencies', ['ngAnimate', 'ngAria', 'ngCookies']);
  angular.module('SEED.vendor_dependencies', [
    'ngTagsInput',
    'ui-notification',
    'ui.bootstrap',
    'ui.grid',
    'ui.grid.draggable-rows',
    'ui.grid.exporter',
    'ui.grid.edit',
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
    'ngSanitize',
    'ngWig'
  ]);
  angular.module('SEED.controllers', [
    'SEED.controller.about',
    'SEED.controller.accounts',
    'SEED.controller.admin',
    'SEED.controller.analyses',
    'SEED.controller.analysis',
    'SEED.controller.analysis_details',
    'SEED.controller.analysis_run',
    'SEED.controller.at_submission_import_modal',
    'SEED.controller.bulk_edit_goalnotes_modal',
    'SEED.controller.bulk_edit_properties_modal',
    'SEED.controller.column_mapping_profile_modal',
    'SEED.controller.column_mappings',
    'SEED.controller.column_settings',
    'SEED.controller.confirm_column_settings_modal',
    'SEED.controller.confirm_organization_deletion_modal',
    'SEED.controller.create_column_modal',
    'SEED.controller.service_modal',
    'SEED.controller.system_modal',
    'SEED.controller.create_organization_modal',
    'SEED.controller.create_sub_organization_modal',
    'SEED.controller.create_facilities_plan_run_modal',
    'SEED.controller.cycle_admin',
    'SEED.controller.data_logger_upload_or_update_modal',
    'SEED.controller.data_quality_admin',
    'SEED.controller.data_quality_labels_modal',
    'SEED.controller.data_quality_modal',
    'SEED.controller.data_upload_audit_template_modal',
    'SEED.controller.data_upload_espm_modal',
    'SEED.controller.data_upload_modal',
    'SEED.controller.data_view',
    'SEED.controller.dataset',
    'SEED.controller.dataset_detail',
    'SEED.controller.delete_column_modal',
    'SEED.controller.delete_cycle_modal',
    'SEED.controller.delete_data_logger_upload_or_update_modal',
    'SEED.controller.delete_dataset_modal',
    'SEED.controller.delete_document_modal',
    'SEED.controller.delete_file_modal',
    'SEED.controller.delete_modal',
    'SEED.controller.update_derived_data_modal',
    'SEED.controller.delete_org_modal',
    'SEED.controller.derived_columns_admin',
    'SEED.controller.derived_columns_editor',
    'SEED.controller.developer',
    'SEED.controller.document_upload_modal',
    'SEED.controller.email_templates',
    'SEED.controller.email_templates_modal',
    'SEED.controller.export_buildingsync_modal',
    'SEED.controller.export_inventory_modal',
    'SEED.controller.export_report_modal',
    'SEED.controller.export_to_audit_template_modal',
    'SEED.controller.export_to_cts_modal',
    'SEED.controller.faq',
    'SEED.controller.filter_group_modal',
    'SEED.controller.geocode_modal',
    'SEED.controller.goal_editor_modal',
    'SEED.controller.green_button_upload_modal',
    'SEED.controller.insights_program',
    'SEED.controller.insights_property',
    'SEED.controller.inventory_column_list_profiles',
    'SEED.controller.inventory_cycles',
    'SEED.controller.inventory_detail',
    'SEED.controller.inventory_detail_analyses',
    'SEED.controller.inventory_detail_analyses_modal',
    'SEED.controller.inventory_detail_column_list_profiles',
    'SEED.controller.inventory_detail_cycles',
    'SEED.controller.inventory_group_list',
    'SEED.controller.inventory_group_detail_dashboard',
    'SEED.controller.inventory_group_detail_meters',
    'SEED.controller.inventory_group_detail_systems',
    'SEED.controller.inventory_group_modal',
    'SEED.controller.inventory_detail_map',
    'SEED.controller.inventory_detail_meters',
    'SEED.controller.inventory_detail_notes_modal',
    'SEED.controller.inventory_detail_sensors',
    'SEED.controller.inventory_detail_timeline',
    'SEED.controller.inventory_detail_ubid',
    'SEED.controller.inventory_list',
    'SEED.controller.inventory_map',
    'SEED.controller.inventory_plots',
    'SEED.controller.inventory_reports',
    'SEED.controller.inventory_summary',
    'SEED.controller.label_admin',
    'SEED.controller.mapping',
    'SEED.controller.members',
    'SEED.controller.menu',
    'SEED.controller.merge_modal',
    'SEED.controller.meter_deletion_modal',
    'SEED.controller.meter_edit_modal',
    'SEED.controller.system_meter_readings_upload_modal',
    'SEED.controller.group_meter_creation_modal',
    'SEED.controller.modified_modal',
    'SEED.controller.move_inventory_modal',
    'SEED.controller.new_member_modal',
    'SEED.controller.notes',
    'SEED.controller.organization',
    'SEED.controller.organization_access_level_tree',
    'SEED.controller.organization_add_access_level_instance_modal',
    'SEED.controller.organization_add_access_level_modal',
    'SEED.controller.organization_delete_access_level_instance_modal',
    'SEED.controller.organization_edit_access_level_instance_modal',
    'SEED.controller.organization_settings',
    'SEED.controller.organization_sharing',
    'SEED.controller.pairing',
    'SEED.controller.pairing_settings',
    'SEED.controller.portfolio_summary',
    'SEED.controller.facilities_plan',
    'SEED.controller.postoffice_modal',
    'SEED.controller.profile',
    'SEED.controller.program_setup',
    'SEED.controller.qr_code_scan_modal',
    'SEED.controller.record_match_merge_link_modal',
    'SEED.controller.rename_column_modal',
    'SEED.controller.report_configuration_modal',
    'SEED.controller.reset_modal',
    'SEED.controller.sample_data_modal',
    'SEED.controller.security',
    'SEED.controller.sensor_delete_modal',
    'SEED.controller.sensor_readings_upload_modal',
    'SEED.controller.sensor_update_modal',
    'SEED.controller.sensors_upload_modal',
    'SEED.controller.set_update_to_now_modal',
    'SEED.controller.settings_profile_modal',
    'SEED.controller.show_populated_columns_modal',
    'SEED.controller.two_factor_profile',
    'SEED.controller.ubid_admin',
    'SEED.controller.ubid_admin_modal',
    'SEED.controller.ubid_decode_modal',
    'SEED.controller.ubid_editor_modal',
    'SEED.controller.ubid_jaccard_index_modal',
    'SEED.controller.unmerge_modal',
    'SEED.controller.update_inventory_groups_modal',
    'SEED.controller.update_item_labels_modal'
  ]);
  angular.module('SEED.filters', [
    'district',
    'floatingPoint',
    'fromNow',
    'getAnalysisRunAuthor',
    'htmlToPlainText',
    'ignoremap',
    'startCase',
    'startFrom',
    'stripImportPrefix',
    'titleCase',
    'tolerantNumber',
    'typedNumber'
  ]);
  angular.module('SEED.directives', [
    'sdBasicPropertyInfoChart',
    'sdCheckCycleExists',
    'sdCheckLabelExists',
    'sdDropdown',
    'sdEnter',
    'sdLabel',
    'sdResizable',
    'sdScrollSync',
    'sdUbid',
    'sdUploader'
  ]);
  angular.module('SEED.services', [
    'SEED.service.ah',
    'SEED.service.analyses',
    'SEED.service.audit_template',
    'SEED.service.auth',
    'SEED.service.column_mappings',
    'SEED.service.columns',
    'SEED.service.compliance_metric',
    'SEED.service.cycle',
    'SEED.service.data_quality',
    'SEED.service.data_view',
    'SEED.service.dataset',
    'SEED.service.derived_columns',
    'SEED.service.element',
    'SEED.service.espm',
    'SEED.service.event',
    'SEED.service.facilities_plan',
    'SEED.service.facilities_plan_run',
    'SEED.service.filter_groups',
    'SEED.service.flippers',
    'SEED.service.geocode',
    'SEED.service.goal',
    'SEED.service.httpParamSerializerSeed',
    'SEED.service.inventory',
    'SEED.service.inventory_group',
    'SEED.service.inventory_reports',
    'SEED.service.label',
    'SEED.service.main',
    'SEED.service.map',
    'SEED.service.mapping',
    'SEED.service.matching',
    'SEED.service.meter',
    'SEED.service.meters',
    'SEED.service.modified',
    'SEED.service.note',
    'SEED.service.organization',
    'SEED.service.pairing',
    'SEED.service.postoffice',
    'SEED.service.property_measure',
    'SEED.service.report_configurations',
    'SEED.service.salesforce_config',
    'SEED.service.salesforce_mapping',
    'SEED.service.scenario',
    'SEED.service.search',
    'SEED.service.sensor',
    'SEED.service.service',
    'SEED.service.system',
    'SEED.service.simple_modal',
    'SEED.service.two_factor',
    'SEED.service.ubid',
    'SEED.service.uniformat',
    'SEED.service.uploader',
    'SEED.service.user'
  ]);
  angular.module('SEED.utilities', ['SEED.utility.spinner']);

  const SEED_app = angular.module(
    'SEED',
    ['SEED.angular_dependencies', 'SEED.vendor_dependencies', 'SEED.filters', 'SEED.directives', 'SEED.services', 'SEED.controllers', 'SEED.utilities', 'SEED.constants'],
    [
      '$interpolateProvider',
      '$qProvider',
      ($interpolateProvider, $qProvider) => {
        $interpolateProvider.startSymbol('{$');
        $interpolateProvider.endSymbol('$}');
        $qProvider.errorOnUnhandledRejections(false);
      }
    ]
  );

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
    ($rootScope, $cookies, $http, $log, $q, $state, $transitions, $translate, editableOptions, modified_service, spinner_utility) => {
      const csrftoken = $cookies.get('csrftoken');
      SEED.csrftoken = csrftoken;
      $http.defaults.headers.common['X-CSRFToken'] = csrftoken;
      $http.defaults.headers.post['X-CSRFToken'] = csrftoken;
      $http.defaults.xsrfCookieName = 'csrftoken';
      $http.defaults.xsrfHeaderName = 'X-CSRFToken';

      // config ANGULAR-XEDITABLE ... (this is the recommended place rather than in .config)...
      editableOptions.theme = 'bs3';

      // Use lodash in views
      $rootScope._ = window._;

      // ui-router transition actions
      $transitions.onStart({}, (/* transition */) => {
        if (modified_service.isModified()) {
          return modified_service
            .showModifiedDialog()
            .then(() => {
              modified_service.resetModified();
            })
            .catch(() => $q.reject('acknowledged modified'));
        }
        spinner_utility.show();
      });

      $transitions.onSuccess({}, (/* transition */) => {
        if ($rootScope.route_load_error && $rootScope.load_error_message === 'Your SEED account is not associated with any organizations. Please contact a SEED administrator.') {
          $state.go('home');
          return;
        }

        $rootScope.route_load_error = false;
        spinner_utility.hide();
      });

      $transitions.onError({}, (transition) => {
        spinner_utility.hide();
        if (transition.error().message === 'The transition was ignored') return;

        // route_load_error already set (User has no associated orgs)
        if ($rootScope.route_load_error && $rootScope.load_error_message === 'Your SEED account is not associated with any organizations. Please contact a SEED administrator.') {
          $state.go('home');
          return;
        }

        const error = transition.error().detail;

        if (error !== 'acknowledged modified') {
          $rootScope.route_load_error = true;

          let message;
          if (_.isString(_.get(error, 'data.message'))) message = _.get(error, 'data.message');
          else if (_.isString(_.get(error, 'data'))) message = _.get(error, 'data');

          if (error === 'not authorized' || error === 'Your page could not be located!') {
            $rootScope.load_error_message = $translate.instant(error);
          } else {
            $rootScope.load_error_message = '' || message || error;
          }
        }

        // Revert the url when the transition was triggered by a sidebar link (options.source === 'url')
        if (transition.options().source === 'url') {
          const $urlRouter = transition.router.urlRouter;

          $urlRouter.push($state.$current.navigable.url, $state.params, { replace: true });
          $urlRouter.update(true);
        }
      });

      $state.defaultErrorHandler((error) => {
        $log.log(error);
      });
    }
  ]);

  /**
   * Create custom UI-Grid templates
   */
  SEED_app.run([
    '$templateCache',
    ($templateCache) => {
      $templateCache.put(
        'ui-grid/seedMergeHeader',
        '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : (!col.sort.direction ? \'none\' : \'other\'))}}"><div role="button" tabindex="0" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex" title="TOOLTIP"><span class="ui-grid-header-cell-label" ui-grid-one-bind-id-grid="col.uid + \'-header-text\'">{{ col.displayName CUSTOM_FILTERS }}</span> <span title="Merge Protection: Favor Existing" ui-grid-visible="col.colDef.merge_protection === \'Favor Existing\'" class="glyphicon glyphicon-lock lock"></span> <span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" ui-grid-visible="col.sort.direction" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-blank\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 )  : null}}" aria-hidden="true"></i> <sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div><div role="button" tabindex="0" ui-grid-one-bind-id-grid="col.uid + \'-menu-button\'" class="ui-grid-column-menu-button" ng-if="grid.options.enableColumnMenus && !col.isRowHeader  && col.colDef.enableColumnMenu !== false" ng-click="toggleMenu($event)" ng-class="{\'ui-grid-column-menu-button-last-col\': isLastCol}" ui-grid-one-bind-aria-label="i18n.headerCell.aria.columnMenuButtonLabel" aria-haspopup="true"><i class="ui-grid-icon-angle-down" aria-hidden="true">&nbsp;</i></div><div ui-grid-filter></div></div>'
      );
    }
  ]);

  /**
   * url routing declaration for SEED
   */
  SEED_app.config([
    'stateHelperProvider',
    '$urlRouterProvider',
    '$locationProvider',
    (stateHelperProvider, $urlRouterProvider, $locationProvider) => {
      const static_url = SEED.urls.STATIC_URL;

      $locationProvider.hashPrefix('');
      $urlRouterProvider.otherwise('/');

      stateHelperProvider
        .state({
          name: 'home',
          url: '/',
          templateUrl: `${static_url}seed/partials/home.html`
        })
        .state({
          name: 'profile',
          url: '/profile',
          templateUrl: `${static_url}seed/partials/profile.html`,
          controller: 'profile_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              '$q',
              'user_service',
              (auth_service, $q, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_superuser']);
              }
            ],
            user_profile_payload: ['user_service', (user_service) => user_service.get_user_profile()]
          }
        })
        .state({
          name: 'two_factor_profile',
          url: '/profile/two_factor_profile',
          templateUrl: `${static_url}seed/partials/two_factor_profile.html`,
          controller: 'two_factor_profile_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_superuser']);
              }
            ],
            organizations_payload: [
              'organization_service',
              (organization_service) => organization_service.get_organizations()
            ],
            user_profile_payload: [
              'user_service',
              (user_service) => user_service.get_user_profile()
            ]
          }
        })
        .state({
          name: 'security',
          url: '/profile/security',
          templateUrl: `${static_url}seed/partials/security.html`,
          controller: 'security_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              '$q',
              'user_service',
              (auth_service, $q, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_superuser']);
              }
            ],
            user_profile_payload: ['user_service', (user_service) => user_service.get_user_profile()]
          }
        })
        .state({
          name: 'developer',
          url: '/profile/developer',
          templateUrl: `${static_url}seed/partials/developer.html`,
          controller: 'developer_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              '$q',
              'user_service',
              (auth_service, $q, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_superuser']);
              }
            ],
            user_profile_payload: ['user_service', (user_service) => user_service.get_user_profile()]
          }
        })
        .state({
          name: 'admin',
          url: '/profile/admin',
          templateUrl: `${static_url}seed/partials/admin.html`,
          controller: 'admin_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              '$q',
              'user_service',
              (auth_service, $q, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_superuser']).then(
                  (data) => {
                    if (data.auth.requires_superuser) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ],
            organizations_payload: [
              'auth_payload',
              'organization_service',
              // Require auth_payload to successfully complete before attempting
              (auth_payload, organization_service) => organization_service.get_organizations()
            ],
            user_profile_payload: ['user_service', (user_service) => user_service.get_user_profile()],
            users_payload: [
              'auth_payload',
              'user_service',
              // Require auth_payload to successfully complete before attempting
              (auth_payload, user_service) => user_service.get_users()
            ]
          }
        })
        .state({
          name: 'analyses',
          url: '/analyses',
          templateUrl: `${static_url}seed/partials/analyses.html`,
          controller: 'analyses_controller',
          resolve: {
            analyses_payload: ['analyses_service', 'user_service', (analyses_service, user_service) => analyses_service.get_analyses_for_org(user_service.get_organization().id)],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            messages_payload: [
              'analyses_service',
              'user_service',
              '$stateParams',
              (analyses_service, user_service) => analyses_service.get_analyses_messages_for_org(user_service.get_organization().id)
            ],
            users_payload: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => organization_service.get_organization_users({ org_id: user_service.get_organization().id })
            ],
            auth_payload: [
              'auth_service',
              'user_service',
              '$q',
              (auth_service, user_service, $q) => auth_service.is_authorized(user_service.get_organization().id, ['requires_owner', 'requires_member']).then(
                (data) => {
                  if (data.auth.requires_member) {
                    return data;
                  }
                  return $q.reject('not authorized');
                },
                (data) => $q.reject(data.message)
              )
            ],
            cycles_payload: ['cycle_service', '$stateParams', (cycle_service, $stateParams) => cycle_service.get_cycles_for_org($stateParams.organization_id)]
          }
        })
        .state({
          name: 'analysis',
          url: '/analyses/{analysis_id:int}',
          templateUrl: `${static_url}seed/partials/analysis.html`,
          controller: 'analysis_controller',
          resolve: {
            analysis_payload: [
              'analyses_service',
              'user_service',
              '$stateParams',
              (analyses_service, user_service, $stateParams) => analyses_service.get_analysis_for_org($stateParams.analysis_id, user_service.get_organization().id)
            ],
            messages_payload: [
              'analyses_service',
              'user_service',
              '$stateParams',
              (analyses_service, user_service, $stateParams) => analyses_service.get_analysis_messages_for_org($stateParams.analysis_id, user_service.get_organization().id)
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            users_payload: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => organization_service.get_organization_users({ org_id: user_service.get_organization().id })
            ],
            views_payload: [
              'analyses_service',
              'user_service',
              '$stateParams',
              (analyses_service, user_service, $stateParams) => analyses_service.get_analysis_views_for_org($stateParams.analysis_id, user_service.get_organization().id)
            ],
            auth_payload: [
              'auth_service',
              'user_service',
              '$q',
              (auth_service, user_service, $q) => auth_service.is_authorized(user_service.get_organization().id, ['requires_owner', 'requires_member']).then(
                (data) => {
                  if (data.auth.requires_member) {
                    return data;
                  }
                  return $q.reject('not authorized');
                },
                (data) => $q.reject(data.message)
              )
            ],
            cycles_payload: ['cycle_service', '$stateParams', (cycle_service, $stateParams) => cycle_service.get_cycles_for_org($stateParams.organization_id)]
          }
        })
        .state({
          name: 'analysis_run',
          url: '/analyses/{analysis_id:int}/runs/{run_id:int}',
          templateUrl: `${static_url}seed/partials/analysis_run.html`,
          controller: 'analysis_run_controller',
          resolve: {
            analysis_payload: [
              'analyses_service',
              'user_service',
              '$stateParams',
              (analyses_service, user_service, $stateParams) => analyses_service.get_analysis_for_org($stateParams.analysis_id, user_service.get_organization().id)
            ],
            messages_payload: [
              'analyses_service',
              'user_service',
              '$stateParams',
              (analyses_service, user_service, $stateParams) => analyses_service.get_analysis_messages_for_org($stateParams.analysis_id, user_service.get_organization().id)
            ],
            view_payload: [
              'analyses_service',
              'user_service',
              '$stateParams',
              (analyses_service, user_service, $stateParams) => analyses_service.get_analysis_view_for_org($stateParams.analysis_id, $stateParams.run_id, user_service.get_organization().id)
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            users_payload: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => organization_service.get_organization_users({ org_id: user_service.get_organization().id })
            ],
            auth_payload: [
              'auth_service',
              'user_service',
              '$q',
              (auth_service, user_service, $q) => auth_service.is_authorized(user_service.get_organization().id, ['requires_owner', 'requires_member']).then(
                (data) => {
                  if (data.auth.requires_member) {
                    return data;
                  }
                  return $q.reject('not authorized');
                },
                (data) => $q.reject(data.message)
              )
            ]
          }
        })
        .state({
          name: 'reports',
          url: '/insights/reports',
          templateUrl: `${static_url}seed/partials/inventory_reports.html`,
          controller: 'inventory_reports_controller',
          resolve: {
            columns: [
              '$stateParams',
              'user_service',
              'inventory_service',
              'naturalSort',
              ($stateParams, user_service, inventory_service, naturalSort) => {
                const organization_id = user_service.get_organization().id;
                return inventory_service.get_property_columns_for_org(organization_id).then((columns) => {
                  columns = _.reject(columns, 'related');
                  columns = _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                  columns.sort((a, b) => naturalSort(a.displayName, b.displayName));
                  return columns;
                });
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            filter_groups: ['filter_groups_service', (filter_service) => filter_service.get_filter_groups('Property')],
            report_configurations: ['report_configurations_service', (report_configurations_service) => report_configurations_service.get_report_configurations()],
            organization_payload: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return organization_service.get_organization(organization_id);
              }
            ],
            access_level_tree: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return organization_service.get_organization_access_level_tree(organization_id);
              }
            ]
          }
        })
        .state({
          name: 'column_list_profiles',
          url: '/{inventory_type:properties|taxlots}/settings',
          templateUrl: `${static_url}seed/partials/inventory_column_list_profiles.html`,
          controller: 'inventory_column_list_profiles_controller',
          resolve: {
            $uibModalInstance: () => ({
              close() {}
            }),
            all_columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns();
                }
                return inventory_service.get_taxlot_columns();
              }
            ],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('List View Profile', inventory_type);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return _.find(profiles, { id: lastProfileId });
                }
                const currentProfile = _.first(profiles);
                if (currentProfile) inventory_service.save_last_profile(currentProfile.id, $stateParams.inventory_type);
                return currentProfile;
              }
            ],
            shared_fields_payload: ['user_service', (user_service) => user_service.get_shared_buildings()]
          }
        })
        .state({
          name: 'detail_column_list_profiles',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}/settings',
          templateUrl: `${static_url}seed/partials/inventory_detail_column_list_profiles.html`,
          controller: 'inventory_detail_column_list_profiles_controller',
          resolve: {
            columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns().then((columns) => {
                    _.remove(columns, 'related');
                    _.remove(columns, { column_name: 'lot_number', table_name: 'PropertyState' });
                    return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                  });
                }
                return inventory_service.get_taxlot_columns().then((columns) => {
                  _.remove(columns, 'related');
                  return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                });
              }
            ],
            derived_columns_payload: [
              'derived_columns_service',
              '$stateParams',
              'user_service',
              (derived_columns_service, $stateParams, user_service) => {
                const organization_id = user_service.get_organization().id;
                return derived_columns_service.get_derived_columns(organization_id, $stateParams.inventory_type);
              }
            ],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('Detail View Profile', inventory_type);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_detail_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return _.find(profiles, { id: lastProfileId });
                }
                const currentProfile = _.first(profiles);
                if (currentProfile) inventory_service.save_last_detail_profile(currentProfile.id, $stateParams.inventory_type);
                return currentProfile;
              }
            ]
          }
        })
        .state({
          name: 'inventory_detail_notes',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}/notes',
          templateUrl: `${static_url}seed/partials/inventory_detail_notes.html`,
          controller: 'notes_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                let promise;
                if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property(view_id);
                else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            inventory_type: ['$stateParams', ($stateParams) => $stateParams.inventory_type],
            view_id: ['$stateParams', ($stateParams) => $stateParams.view_id],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            notes: [
              '$stateParams',
              'note_service',
              'user_service',
              ($stateParams, note_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return note_service.get_notes(organization_id, $stateParams.inventory_type, $stateParams.view_id);
              }
            ],
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']);
              }
            ],
            $uibModalInstance: () => undefined
          }
        })
        .state({
          name: 'inventory_detail_ubid',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}/ubids',
          templateUrl: `${static_url}seed/partials/inventory_detail_ubid.html`,
          controller: 'inventory_detail_ubid_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                let promise;
                if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property(view_id);
                else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)]
          }
        })
        .state({
          name: 'mapping',
          url: '/data/mapping/{importfile_id:int}',
          templateUrl: `${static_url}seed/partials/mapping.html`,
          controller: 'mapping_controller',
          resolve: {
            column_mapping_profiles_payload: [
              'column_mappings_service',
              'user_service',
              'COLUMN_MAPPING_PROFILE_TYPE_NORMAL',
              'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT',
              'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM',
              'import_file_payload',
              (
                column_mappings_service,
                user_service,
                COLUMN_MAPPING_PROFILE_TYPE_NORMAL,
                COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT,
                COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM,
                import_file_payload
              ) => {
                let filter_profile_types;
                if (import_file_payload.import_file.source_type === 'BuildingSync Raw') {
                  filter_profile_types = [COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT, COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM];
                } else {
                  filter_profile_types = [COLUMN_MAPPING_PROFILE_TYPE_NORMAL];
                }
                const organization_id = user_service.get_organization().id;
                return column_mappings_service.get_column_mapping_profiles_for_org(organization_id, filter_profile_types).then((response) => response.data);
              }
            ],
            import_file_payload: [
              'dataset_service',
              '$stateParams',
              (dataset_service, $stateParams) => {
                const { importfile_id } = $stateParams;
                return dataset_service.get_import_file(importfile_id);
              }
            ],
            suggested_mappings_payload: [
              'mapping_service',
              '$stateParams',
              (mapping_service, $stateParams) => {
                const { importfile_id } = $stateParams;
                return mapping_service.get_column_mapping_suggestions(importfile_id);
              }
            ],
            raw_columns_payload: [
              'mapping_service',
              '$stateParams',
              (mapping_service, $stateParams) => {
                const { importfile_id } = $stateParams;
                return mapping_service.get_raw_columns(importfile_id);
              }
            ],
            first_five_rows_payload: [
              'mapping_service',
              '$stateParams',
              (mapping_service, $stateParams) => {
                const { importfile_id } = $stateParams;
                return mapping_service.get_first_five_rows(importfile_id);
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            matching_criteria_columns_payload: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => organization_service.matching_criteria_columns(user_service.get_organization().id)
            ],
            auth_payload: [
              'auth_service',
              '$q',
              'user_service',
              (auth_service, $q, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']).then(
                  (data) => {
                    if (data.auth.requires_member) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            derived_columns_payload: [
              'derived_columns_service',
              '$stateParams',
              'user_service',
              (derived_columns_service, $stateParams, user_service) => {
                const organization_id = user_service.get_organization().id;
                return derived_columns_service.get_derived_columns(organization_id, $stateParams.inventory_type);
              }
            ]
          }
        })
        .state({
          name: 'pairing',
          url: '/data/pairing/{importfile_id:int}/{inventory_type:properties|taxlots}',
          templateUrl: `${static_url}seed/partials/pairing.html`,
          controller: 'pairing_controller',
          resolve: {
            import_file_payload: [
              'dataset_service',
              '$stateParams',
              (dataset_service, $stateParams) => {
                const { importfile_id } = $stateParams;
                return dataset_service.get_import_file(importfile_id);
              }
            ],
            allPropertyColumns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => inventory_service.get_property_columns().then((columns) => {
                columns = _.reject(columns, 'related');
                return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
              })
            ],
            allTaxlotColumns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => inventory_service.get_taxlot_columns().then((columns) => {
                columns = _.reject(columns, 'related');
                return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
              })
            ],
            propertyInventory: ['inventory_service', (inventory_service) => inventory_service.get_properties(1, undefined, undefined, -1)],
            taxlotInventory: ['inventory_service', (inventory_service) => inventory_service.get_taxlots(1, undefined, undefined, -1)],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()]
          }
        })
        .state({
          name: 'pairing_settings',
          url: '/data/pairing/{importfile_id:int}/{inventory_type:properties|taxlots}/settings',
          templateUrl: `${static_url}seed/partials/pairing_settings.html`,
          controller: 'pairing_settings_controller',
          resolve: {
            import_file_payload: [
              'dataset_service',
              '$stateParams',
              (dataset_service, $stateParams) => {
                const { importfile_id } = $stateParams;
                return dataset_service.get_import_file(importfile_id);
              }
            ],
            propertyColumns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => inventory_service.get_property_columns().then((columns) => {
                columns = _.reject(columns, 'related');
                return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
              })
            ],
            taxlotColumns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => inventory_service.get_taxlot_columns().then((columns) => {
                columns = _.reject(columns, 'related');
                return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
              })
            ]
          }
        })
        .state({
          name: 'dataset_list',
          url: '/data',
          templateUrl: `${static_url}seed/partials/dataset_list.html`,
          controller: 'dataset_list_controller',
          resolve: {
            datasets_payload: ['dataset_service', (dataset_service) => dataset_service.get_datasets()],
            auth_payload: [
              'auth_service',
              '$q',
              'user_service',
              (auth_service, $q, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']).then(
                  (data) => {
                    if (data.auth.requires_member) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'dataset_detail',
          url: '/data/{dataset_id:int}',
          templateUrl: `${static_url}seed/partials/dataset_detail.html`,
          controller: 'dataset_detail_controller',
          resolve: {
            dataset_payload: [
              'dataset_service',
              '$stateParams',
              '$state',
              '$q',
              'spinner_utility',
              (dataset_service, $stateParams, $state, $q, spinner_utility) => dataset_service.get_dataset($stateParams.dataset_id).catch((response) => {
                if (response.status === 400 && response.data.message === 'Organization ID mismatch between dataset and organization') {
                  // Org id mismatch, likely due to switching organizations while viewing a dataset_detail page
                  _.delay(() => {
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
              })
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            auth_payload: [
              'auth_service',
              '$q',
              'user_service',
              (auth_service, $q, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']).then(
                  (data) => {
                    if (data.auth.requires_member) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'contact',
          url: '/contact',
          templateUrl: `${static_url}seed/partials/contact.html`
        })
        .state({
          name: 'api_docs',
          url: '/api/swagger',
          templateUrl: `${static_url}seed/partials/api_docs.html`
        })
        .state({
          name: 'about',
          url: '/about',
          templateUrl: `${static_url}seed/partials/about.html`,
          controller: 'about_controller',
          resolve: {
            version_payload: ['main_service', (main_service) => main_service.version()]
          }
        })
        .state({
          name: 'organizations',
          url: '/accounts',
          templateUrl: `${static_url}seed/partials/accounts.html`,
          controller: 'accounts_controller',
          resolve: {
            organization_payload: ['organization_service', (organization_service) => organization_service.get_organizations()]
          }
        })
        .state({
          name: 'organization_settings',
          url: '/accounts/{organization_id:int}',
          templateUrl: `${static_url}seed/partials/organization_settings.html`,
          controller: 'organization_settings_controller',
          resolve: {
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            property_column_names: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const { organization_id } = $stateParams;
                return inventory_service.get_property_column_names_and_ids_for_org(organization_id);
              }
            ],
            taxlot_column_names: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const { organization_id } = $stateParams;
                return inventory_service.get_taxlot_column_names_for_org(organization_id);
              }
            ],
            labels_payload: [
              'label_service',
              '$stateParams',
              (label_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return label_service.get_labels_for_org(organization_id);
              }
            ],
            salesforce_mappings_payload: [
              'salesforce_mapping_service',
              '$stateParams',
              (salesforce_mapping_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return salesforce_mapping_service.get_salesforce_mappings(organization_id);
              }
            ],
            salesforce_configs_payload: [
              'salesforce_config_service',
              '$stateParams',
              (salesforce_config_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return salesforce_config_service.get_salesforce_configs(organization_id);
              }
            ],
            audit_template_configs_payload: [
              'audit_template_service',
              '$stateParams',
              (audit_template_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return audit_template_service.get_audit_template_configs(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ],
            property_columns: ['inventory_service', 'user_service', (inventory_service) => inventory_service.get_property_columns()],
            facilities_plans: ['facilities_plan_service', (facilities_plan_service) => facilities_plan_service.get_facilities_plans()]
          }
        })
        .state({
          name: 'organization_sharing',
          url: '/accounts/{organization_id:int}/sharing',
          templateUrl: `${static_url}seed/partials/organization_sharing.html`,
          controller: 'organization_sharing_controller',
          resolve: {
            all_columns: [
              '$stateParams',
              'analyses_service',
              ($stateParams, analyses_service) => {
                const { organization_id } = $stateParams;
                return analyses_service.get_used_columns(organization_id);
              }
            ],
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            query_threshold_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_query_threshold(organization_id);
              }
            ],
            shared_fields_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_shared_fields(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'programs',
          url: '/accounts/{organization_id:int}/program_setup',
          templateUrl: `${static_url}seed/partials/program_setup.html`,
          controller: 'program_setup_controller',
          resolve: {
            valid_column_data_types: [() => ['number', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean']],
            valid_x_axis_data_types: [() => ['number', 'string', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean']],
            compliance_metrics: [
              '$stateParams',
              'compliance_metric_service',
              ($stateParams, compliance_metric_service) => compliance_metric_service.get_compliance_metrics($stateParams.organization_id)
            ],
            organization_payload: ['organization_service', '$stateParams', (organization_service, $stateParams) => organization_service.get_organization($stateParams.organization_id)],
            cycles_payload: ['cycle_service', '$stateParams', (cycle_service, $stateParams) => cycle_service.get_cycles_for_org($stateParams.organization_id)],
            property_columns: [
              'valid_column_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_column_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_property_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_column_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            x_axis_columns: [
              'valid_x_axis_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_x_axis_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_property_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_x_axis_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            filter_groups: [
              '$stateParams',
              'filter_groups_service',
              ($stateParams, filter_groups_service) => {
                const inventory_type = 'Property'; // just properties for now
                return filter_groups_service.get_filter_groups(inventory_type, $stateParams.organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => auth_service.is_authorized($stateParams.organization_id, ['requires_member']).then(
                (data) => {
                  if (data.auth.requires_member) {
                    return data;
                  }
                  return $q.reject('not authorized');
                },
                (data) => $q.reject(data.message)
              )
            ]
          }
        })
        .state({
          name: 'program_setup',
          url: '/accounts/{organization_id:int}/program_setup/{id:int}',
          templateUrl: `${static_url}seed/partials/program_setup.html`,
          controller: 'program_setup_controller',
          resolve: {
            valid_column_data_types: [() => ['number', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean']],
            valid_x_axis_data_types: [() => ['number', 'string', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean']],
            compliance_metrics: [
              '$stateParams',
              'compliance_metric_service',
              ($stateParams, compliance_metric_service) => compliance_metric_service.get_compliance_metrics($stateParams.organization_id)
            ],
            organization_payload: ['organization_service', '$stateParams', (organization_service, $stateParams) => organization_service.get_organization($stateParams.organization_id)],
            cycles_payload: ['cycle_service', '$stateParams', (cycle_service, $stateParams) => cycle_service.get_cycles_for_org($stateParams.organization_id)],
            property_columns: [
              'valid_column_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_column_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_property_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_column_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            x_axis_columns: [
              'valid_x_axis_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_x_axis_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_property_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_x_axis_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            filter_groups: [
              '$stateParams',
              'filter_groups_service',
              ($stateParams, filter_groups_service) => {
                const inventory_type = 'Property'; // just properties for now
                return filter_groups_service.get_filter_groups(inventory_type, $stateParams.organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => auth_service.is_authorized($stateParams.organization_id, ['requires_member']).then(
                (data) => {
                  if (data.auth.requires_member) {
                    return data;
                  }
                  return $q.reject('not authorized');
                },
                (data) => $q.reject(data.message)
              )
            ]
          }
        })
        .state({
          name: 'organization_access_level_tree',
          url: '/accounts/{organization_id:int}/access_level_tree',
          templateUrl: `${static_url}seed/partials/organization_access_level_tree.html`,
          controller: 'organization_access_level_tree_controller',
          resolve: {
            organization_payload: [
              'organization_service',
              '$stateParams',
              '$q',
              (organization_service, $stateParams, $q) => {
                const organization_id = $stateParams.organization_id;
                return organization_service.get_organization(organization_id).then((data) => {
                  if (data.organization.is_parent) {
                    return data;
                  }
                  return $q.reject('Your page could not be located!');
                });
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const organization_id = $stateParams.organization_id;
                return auth_service.is_authorized(organization_id, ['requires_viewer', 'requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_viewer) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ],
            access_level_tree: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const organization_id = $stateParams.organization_id;
                return organization_service.get_organization_access_level_tree(organization_id);
              }
            ]
          }
        })
        .state({
          name: 'organization_column_settings',
          url: '/accounts/{organization_id:int}/column_settings/{inventory_type:properties|taxlots}',
          templateUrl: `${static_url}seed/partials/column_settings.html`,
          controller: 'column_settings_controller',
          resolve: {
            all_columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const { organization_id } = $stateParams;

                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns_for_org(organization_id, false, false);
                }
                return inventory_service.get_taxlot_columns_for_org(organization_id, false, false);
              }
            ],
            columns: [
              'all_columns',
              'naturalSort',
              (all_columns, naturalSort) => {
                let columns = _.reject(all_columns, 'related');
                columns = _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                columns.sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              }
            ],
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_viewer', 'requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_viewer) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'organization_column_mappings',
          url: '/accounts/{organization_id:int}/column_mappings/{inventory_type:properties|taxlots}',
          templateUrl: `${static_url}seed/partials/column_mappings.html`,
          controller: 'column_mappings_controller',
          resolve: {
            mappable_property_columns_payload: ['inventory_service', (inventory_service) => inventory_service.get_mappable_property_columns().then((result) => result)],
            mappable_taxlot_columns_payload: ['inventory_service', (inventory_service) => inventory_service.get_mappable_taxlot_columns().then((result) => result)],
            column_mapping_profiles_payload: [
              'column_mappings_service',
              '$stateParams',
              (column_mappings_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return column_mappings_service.get_column_mapping_profiles_for_org(organization_id).then((response) => response.data);
              }
            ],
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_viewer', 'requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_viewer) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'organization_data_quality',
          url: '/accounts/{organization_id:int}/data_quality/{rule_type:properties|taxlots|goals}',
          templateUrl: `${static_url}seed/partials/data_quality_admin.html`,
          controller: 'data_quality_admin_controller',
          resolve: {
            columns: [
              '$stateParams',
              'inventory_service',
              'naturalSort',
              ($stateParams, inventory_service, naturalSort) => {
                const { organization_id } = $stateParams;
                if ($stateParams.rule_type === 'properties' || $stateParams.rule_type === 'goals') {
                  return inventory_service.get_property_columns_for_org(organization_id).then((columns) => {
                    columns = _.reject(columns, 'related');
                    columns = _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                    columns.sort((a, b) => naturalSort(a.displayName, b.displayName));
                    return columns;
                  });
                }
                if ($stateParams.rule_type === 'taxlots') {
                  return inventory_service.get_taxlot_columns_for_org(organization_id).then((columns) => {
                    columns = _.reject(columns, 'related');
                    columns = _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                    columns.sort((a, b) => naturalSort(a.displayName, b.displayName));
                    return columns;
                  });
                }
              }
            ],
            used_columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const { organization_id } = $stateParams;
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns_for_org(organization_id, true).then((columns) => {
                    columns = _.reject(columns, 'related');
                    columns = _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                    return columns;
                  });
                }
                return inventory_service.get_taxlot_columns_for_org(organization_id, true).then((columns) => {
                  columns = _.reject(columns, 'related');
                  columns = _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                  return columns;
                });
              }
            ],
            derived_columns_payload: [
              'derived_columns_service',
              '$stateParams',
              (derived_columns_service, $stateParams) => derived_columns_service.get_derived_columns($stateParams.organization_id, $stateParams.inventory_type)
            ],
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            data_quality_rules_payload: [
              'data_quality_service',
              '$stateParams',
              (data_quality_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return data_quality_service.data_quality_rules(organization_id);
              }
            ],
            labels_payload: [
              'label_service',
              '$stateParams',
              (label_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return label_service.get_labels_for_org(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'organization_cycles',
          url: '/accounts/{organization_id:int}/cycles',
          templateUrl: `${static_url}seed/partials/cycle_admin.html`,
          controller: 'cycle_admin_controller',
          resolve: {
            organization_payload: ['organization_service', '$stateParams', (organization_service, $stateParams) => organization_service.get_organization($stateParams.organization_id)],
            cycles_payload: ['cycle_service', '$stateParams', (cycle_service, $stateParams) => cycle_service.get_cycles_for_org($stateParams.organization_id)],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'organization_labels',
          url: '/accounts/{organization_id:int}/labels',
          templateUrl: `${static_url}seed/partials/label_admin.html`,
          controller: 'label_admin_controller',
          resolve: {
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            labels_payload: [
              'label_service',
              '$stateParams',
              (label_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return label_service.get_labels_for_org(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'organization_sub_orgs',
          url: '/accounts/{organization_id:int}/sub_org',
          templateUrl: `${static_url}seed/partials/sub_org.html`,
          controller: 'organization_controller',
          resolve: {
            users_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization_users({ org_id: organization_id });
              }
            ],
            organization_payload: [
              'organization_service',
              '$stateParams',
              '$q',
              (organization_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id).then((data) => {
                  if (data.organization.is_parent) {
                    return data;
                  }
                  return $q.reject('Your page could not be located!');
                });
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'organization_members',
          url: '/accounts/{organization_id:int}/members',
          templateUrl: `${static_url}seed/partials/members.html`,
          controller: 'members_controller',
          resolve: {
            users_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization_users({ org_id: organization_id });
              }
            ],
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['can_invite_member', 'can_remove_member', 'requires_owner', 'requires_member', 'requires_superuser']).then(
                  (data) => {
                    if (data.auth.requires_member) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ],
            user_profile_payload: ['user_service', (user_service) => user_service.get_user_profile()],
            access_level_tree: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const organization_id = $stateParams.organization_id;
                return organization_service.get_organization_access_level_tree(organization_id);
              }
            ]
          }
        })
        .state({
          name: 'organization_email_templates',
          url: '/accounts/{organization_id:int}/email_templates',
          templateUrl: `${static_url}seed/partials/email_templates.html`,
          controller: 'email_templates_controller',
          resolve: {
            organization_payload: ['organization_service', '$stateParams', (organization_service, $stateParams) => organization_service.get_organization($stateParams.organization_id)],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ],
            templates_payload: ['postoffice_service', '$stateParams', (postoffice_service, $stateParams) => postoffice_service.get_templates_for_org($stateParams.organization_id)],
            current_template: [
              'postoffice_service',
              'templates_payload',
              '$stateParams',
              (postoffice_service, templates_payload, $stateParams) => {
                const validTemplateIds = _.map(templates_payload, 'id');
                const lastTemplateId = postoffice_service.get_last_template($stateParams.organization_id);
                if (_.includes(validTemplateIds, lastTemplateId)) {
                  return _.find(templates_payload, { id: lastTemplateId });
                }
                const currentTemplate = _.first(templates_payload);
                if (currentTemplate) postoffice_service.save_last_template(currentTemplate.id, $stateParams.organization_id);
                return currentTemplate;
              }
            ]
          }
        })
        .state({
          name: 'organization_derived_columns',
          url: '/accounts/{organization_id:int}/derived_columns/{inventory_type:properties|taxlots}',
          templateUrl: `${static_url}seed/partials/derived_columns_admin.html`,
          controller: 'derived_columns_admin_controller',
          resolve: {
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            derived_columns_payload: [
              'derived_columns_service',
              '$stateParams',
              (derived_columns_service, $stateParams) => derived_columns_service.get_derived_columns($stateParams.organization_id, $stateParams.inventory_type)
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'organization_derived_column_editor',
          url: '/accounts/{organization_id:int}/derived_columns/edit/:derived_column_id',
          templateUrl: `${static_url}seed/partials/derived_columns_editor.html`,
          controller: 'derived_columns_editor_controller',
          params: {
            inventory_type: 'properties'
          },
          resolve: {
            organization_payload: [
              'organization_service',
              '$stateParams',
              (organization_service, $stateParams) => {
                const { organization_id } = $stateParams;
                return organization_service.get_organization(organization_id);
              }
            ],
            derived_column_payload: [
              'derived_columns_service',
              '$stateParams',
              (derived_columns_service, $stateParams) => {
                if ($stateParams.derived_column_id === undefined) {
                  return {};
                }

                return derived_columns_service.get_derived_column($stateParams.organization_id, $stateParams.derived_column_id);
              }
            ],
            derived_columns_payload: [
              '$stateParams',
              'user_service',
              'derived_columns_service',
              ($stateParams, user_service, derived_columns_service) => {
                const organization_id = user_service.get_organization().id;
                return derived_columns_service.get_derived_columns(organization_id, $stateParams.inventory_type);
              }
            ],
            property_columns_payload: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => inventory_service.get_property_columns_for_org($stateParams.organization_id, false, false)
            ],
            taxlot_columns_payload: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => inventory_service.get_taxlot_columns_for_org($stateParams.organization_id, false, false)
            ],
            auth_payload: [
              'auth_service',
              '$stateParams',
              '$q',
              (auth_service, $stateParams, $q) => {
                const { organization_id } = $stateParams;
                return auth_service.is_authorized(organization_id, ['requires_owner']).then(
                  (data) => {
                    if (data.auth.requires_owner) {
                      return data;
                    }
                    return $q.reject('not authorized');
                  },
                  (data) => $q.reject(data.message)
                );
              }
            ]
          }
        })
        .state({
          name: 'inventory_groups',
          url: '/{inventory_type:properties|taxlots}/groups',
          templateUrl: `${static_url}seed/partials/inventory_groups_list.html`,
          controller: 'inventory_group_list_controller',
          resolve: {
            access_level_tree: [
              'organization_service', 'user_service',
              (organization_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return organization_service.get_descendant_access_level_tree(organization_id);
              }
            ],
            inventory_groups: ['$stateParams', 'inventory_group_service', ($stateParams, inventory_group_service) => {
              const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
              return inventory_group_service.get_groups(inventory_type);
            }],
            current_inventory_group: ['$stateParams', 'inventory_group_service', 'inventory_groups', 'inventory_service', ($stateParams, inventory_group_service, inventory_groups, inventory_service) => {
              const validGroupIds = _.map(inventory_groups, 'id');
              const lastGroupId = inventory_service.get_last_inventory_group($stateParams.inventory_type);
              if (_.includes(validGroupIds, lastGroupId)) {
                return _.find(inventory_groups, { id: lastGroupId });
              }
              const currentInventoryGroup = _.first(inventory_groups);
              if (currentInventoryGroup) inventory_service.save_last_inventory_group(currentInventoryGroup.id, $stateParams.inventory_type);
              return currentInventoryGroup;
            }],
            organization_payload: [
              'user_service',
              'organization_service',
              (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)
            ]
          }
        })
        .state({
          name: 'inventory_list',
          url: '/{inventory_type:properties|taxlots}',
          templateUrl: `${static_url}seed/partials/inventory_list.html`,
          controller: 'inventory_list_controller',
          resolve: {
            access_level_tree: [
              'organization_service', 'user_service',
              (organization_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return organization_service.get_organization_access_level_tree(organization_id);
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('List View Profile', inventory_type, true);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return inventory_service.get_column_list_profile(lastProfileId);
                }
                const currentProfileId = _.first(profiles)?.id;
                if (currentProfileId) {
                  inventory_service.save_last_profile(currentProfileId, $stateParams.inventory_type);
                  return inventory_service.get_column_list_profile(currentProfileId);
                }
                return null;
              }
            ],
            filter_groups: [
              '$stateParams',
              'filter_groups_service',
              ($stateParams, filter_groups_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return filter_groups_service.get_filter_groups(inventory_type);
              }
            ],
            current_filter_group: [
              '$stateParams',
              'filter_groups_service',
              'filter_groups',
              ($stateParams, filter_groups_service, filter_groups) => {
                const validFilterGroupIds = _.map(filter_groups, 'id');
                const lastFilterGroupId = filter_groups_service.get_last_filter_group($stateParams.inventory_type);
                if (_.includes(validFilterGroupIds, lastFilterGroupId)) {
                  return filter_groups_service.get_filter_group(lastFilterGroupId);
                }
                return null;
              }
            ],
            all_columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns();
                }
                return inventory_service.get_taxlot_columns();
              }
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization_brief(user_service.get_organization().id)],
            inventory_groups: [
              '$stateParams',
              'inventory_group_service',
              ($stateParams, inventory_group_service) => inventory_group_service.get_groups_for_inventory($stateParams.inventory_type, [])
            ],
            inventory_group_tab: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                inventory_service.save_last_inventory_group(-1);
                return -1;
              }
            ],
            group: () => null
          }
        })
        .state({
          name: 'inventory_groups_inventory_list',
          url: '/{inventory_type:properties|taxlots}/groups/{group_id:int}/inventory',
          templateUrl: `${static_url}seed/partials/inventory_list.html`,
          controller: 'inventory_list_controller',
          resolve: {
            access_level_tree: [
              'organization_service', 'user_service',
              (organization_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return organization_service.get_organization_access_level_tree(organization_id);
              }
            ],
            cycles: [
              'cycle_service',
              (cycle_service) => cycle_service.get_cycles()
            ],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('List View Profile', inventory_type, true);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return inventory_service.get_column_list_profile(lastProfileId);
                }
                const currentProfileId = _.first(profiles)?.id;
                if (currentProfileId) {
                  inventory_service.save_last_profile(currentProfileId, $stateParams.inventory_type);
                  return inventory_service.get_column_list_profile(currentProfileId);
                }
                return null;
              }
            ],
            filter_groups: [
              '$stateParams',
              'filter_groups_service',
              ($stateParams, filter_groups_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return filter_groups_service.get_filter_groups(inventory_type);
              }
            ],
            current_filter_group: [
              '$stateParams',
              'filter_groups_service',
              'filter_groups',
              ($stateParams, filter_groups_service, filter_groups) => {
                const validFilterGroupIds = _.map(filter_groups, 'id');
                const lastFilterGroupId = filter_groups_service.get_last_filter_group($stateParams.inventory_type);
                if (_.includes(validFilterGroupIds, lastFilterGroupId)) {
                  return filter_groups_service.get_filter_group(lastFilterGroupId);
                }
                return null;
              }
            ],
            all_columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns();
                }
                return inventory_service.get_taxlot_columns();
              }
            ],
            organization_payload: [
              'user_service',
              'organization_service',
              (user_service, organization_service) => organization_service.get_organization_brief(user_service.get_organization().id)
            ],
            derived_columns_payload: [
              '$stateParams',
              'derived_columns_service',
              'organization_payload',
              ($stateParams, derived_columns_service, organization_payload) => derived_columns_service.get_derived_columns(organization_payload.organization.id, $stateParams.inventory_type)
            ],
            inventory_groups: [
              '$stateParams',
              'inventory_group_service',
              ($stateParams, inventory_group_service) => inventory_group_service.get_groups_for_inventory($stateParams.inventory_type, [])
            ],
            inventory_group_tab: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                inventory_service.save_last_inventory_group(-1);
                return -1;
              }
            ],
            group: [
              '$stateParams', 'inventory_group_service', 'user_service',
              ($stateParams, inventory_group_service, user_service) => inventory_group_service.get_group(user_service.get_organization().id, $stateParams.group_id)
            ]
          }
        })
        .state({
          name: 'inventory_map',
          url: '/{inventory_type:properties|taxlots}/map',
          templateUrl: `${static_url}seed/partials/inventory_map.html`,
          controller: 'inventory_map_controller',
          resolve: {
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            labels: [
              '$stateParams',
              'label_service',
              ($stateParams, label_service) => label_service.get_labels($stateParams.inventory_type).then((labels) => _.filter(labels, (label) => !_.isEmpty(label.is_applied)))
            ],
            group: () => null
          }
        })
        .state({
          name: 'inventory_group_map',
          url: '/{inventory_type:properties|taxlots}/groups/{group_id:int}/map',
          templateUrl: `${static_url}seed/partials/inventory_map.html`,
          controller: 'inventory_map_controller',
          resolve: {
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            labels: [
              '$stateParams',
              'label_service',
              ($stateParams, label_service) => label_service.get_labels($stateParams.inventory_type).then((labels) => _.filter(labels, (label) => !_.isEmpty(label.is_applied)))
            ],
            group: [
              '$stateParams', 'inventory_group_service', 'user_service',
              ($stateParams, inventory_group_service, user_service) => inventory_group_service.get_group(user_service.get_organization().id, $stateParams.group_id)
            ]
          }
        })
        .state({
          name: 'inventory_summary',
          url: '/{inventory_type:properties|taxlots}/summary',
          templateUrl: `${static_url}seed/partials/inventory_summary.html`,
          controller: 'inventory_summary_controller',
          resolve: {
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()]
          }
        })
        .state({
          name: 'inventory_plots',
          url: '/{inventory_type:properties|taxlots}/plots',
          templateUrl: `${static_url}seed/partials/inventory_plots.html`,
          controller: 'inventory_plots_controller',
          resolve: {
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('List View Profile', inventory_type, true);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return inventory_service.get_column_list_profile(lastProfileId);
                }
                const currentProfileId = _.first(profiles)?.id;
                if (currentProfileId) {
                  inventory_service.save_last_profile(currentProfileId, $stateParams.inventory_type);
                  return inventory_service.get_column_list_profile(currentProfileId);
                }
                return null;
              }
            ],
            all_columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns();
                }
                return inventory_service.get_taxlot_columns();
              }
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization_brief(user_service.get_organization().id)],
            derived_columns_payload: [
              '$stateParams',
              'derived_columns_service',
              'organization_payload',
              ($stateParams, derived_columns_service, organization_payload) => derived_columns_service.get_derived_columns(organization_payload.organization.id, $stateParams.inventory_type)
            ]
          }
        })
        .state({
          name: 'inventory_cycles',
          url: '/{inventory_type:properties|taxlots}/cycles',
          templateUrl: `${static_url}seed/partials/inventory_cycles.html`,
          controller: 'inventory_cycles_controller',
          resolve: {
            inventory: [
              '$stateParams',
              'inventory_service',
              'current_profile',
              ($stateParams, inventory_service, current_profile) => {
                const last_selected_cycle_ids = inventory_service.get_last_selected_cycles() || [];
                const profile_id = _.has(current_profile, 'id') ? current_profile.id : undefined;
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.properties_cycle(profile_id, last_selected_cycle_ids);
                }
                return inventory_service.taxlots_cycle(profile_id, last_selected_cycle_ids);
              }
            ],
            matching_criteria_columns: [
              'user_service',
              'organization_service',
              (user_service, organization_service) => {
                const org_id = user_service.get_organization().id;
                return organization_service.matching_criteria_columns(org_id);
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('List View Profile', inventory_type);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return _.find(profiles, { id: lastProfileId });
                }
                const currentProfile = _.first(profiles);
                if (currentProfile) inventory_service.save_last_profile(currentProfile.id, $stateParams.inventory_type);
                return currentProfile;
              }
            ],
            all_columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns();
                }
                return inventory_service.get_taxlot_columns();
              }
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)]
          }
        })
        .state({
          name: 'inventory_group_detail_dashboard',
          url: '/{inventory_type:properties|taxlots}/groups/{group_id:int}',
          templateUrl: `${static_url}seed/partials/inventory_group_detail_dashboard.html`,
          controller: 'inventory_group_detail_dashboard_controller',
          resolve: {
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            group: [
              '$stateParams', 'inventory_group_service', 'user_service',
              ($stateParams, inventory_group_service, user_service) => inventory_group_service.get_group(user_service.get_organization().id, $stateParams.group_id)
            ]
          }
        })
        .state({
          name: 'inventory_group_detail_meters',
          url: '/{inventory_type:properties|taxlots}/groups/{group_id:int}/meters',
          templateUrl: `${static_url}seed/partials/inventory_group_detail_meters.html`,
          controller: 'inventory_group_detail_meters_controller',
          resolve: {
            inventory_payload: () => null,
            property_meter_usage: [
              '$stateParams',
              'inventory_group_service',
              ($stateParams, inventory_group_service) => inventory_group_service.get_meter_usage($stateParams.group_id, 'Exact')
            ],
            meters: [
              '$stateParams',
              'inventory_group_service',
              ($stateParams, inventory_group_service) => inventory_group_service.get_meters_for_group($stateParams.group_id)
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            group: [
              '$stateParams', 'inventory_group_service', 'user_service',
              ($stateParams, inventory_group_service, user_service) => inventory_group_service.get_group(user_service.get_organization().id, $stateParams.group_id)
            ],
            columns: [
              '$stateParams',
              'inventory_service',
              'user_service',
              ($stateParams, inventory_service, user_service) => {
                const org_id = user_service.get_organization().id;
                return inventory_service.get_property_column_names_for_org(org_id);
              }
            ]
          }
        })
        .state({
          name: 'inventory_group_detail_systems',
          url: '/{inventory_type:properties|taxlots}/groups/{group_id:int}/systems',
          templateUrl: `${static_url}seed/partials/inventory_group_detail_systems.html`,
          controller: 'inventory_group_detail_systems_controller',
          resolve: {
            systems: ['$stateParams', 'system_service', 'user_service', ($stateParams, system_service, user_service) => {
              const organization_id = user_service.get_organization().id;
              const { group_id } = $stateParams;
              return system_service.get_systems_by_type(organization_id, group_id);
            }],
            organization_payload: [
              'user_service',
              'organization_service',
              (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            group: [
              '$stateParams', 'inventory_group_service', 'user_service',
              ($stateParams, inventory_group_service, user_service) => inventory_group_service.get_group(user_service.get_organization().id, $stateParams.group_id)
            ]
          }
        })
        .state({
          name: 'inventory_detail',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}',
          templateUrl: `${static_url}seed/partials/inventory_detail.html`,
          controller: 'inventory_detail_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                let promise;
                if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property(view_id);
                else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            views_payload: [
              '$stateParams',
              'user_service',
              'inventory_service',
              'inventory_payload',
              ($stateParams, user_service, inventory_service, inventory_payload) => {
                const organization_id = user_service.get_organization().id;
                let promise;
                if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property_views(organization_id, inventory_payload.property.id);
                else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot_views(organization_id, inventory_payload.taxlot.id);

                return promise;
              }
            ],
            analyses_payload: [
              'inventory_service',
              'analyses_service',
              '$stateParams',
              'inventory_payload',
              (inventory_service, analyses_service, $stateParams, inventory_payload) => {
                if ($stateParams.inventory_type !== 'properties') return [];
                return analyses_service.get_analyses_for_canonical_property(inventory_payload.property.id);
              }
            ],
            columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns().then((columns) => {
                    _.remove(columns, 'related');
                    _.remove(columns, { column_name: 'lot_number', table_name: 'PropertyState' });
                    return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                  });
                }
                return inventory_service.get_taxlot_columns().then((columns) => {
                  _.remove(columns, 'related');
                  return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                });
              }
            ],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('Detail View Profile', inventory_type);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_detail_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return _.find(profiles, { id: lastProfileId });
                }
                const currentProfile = _.first(profiles);
                if (currentProfile) inventory_service.save_last_detail_profile(currentProfile.id, $stateParams.inventory_type);
                return currentProfile;
              }
            ],
            labels_payload: [
              '$stateParams',
              'inventory_payload',
              'label_service',
              ($stateParams, inventory_payload, label_service) => label_service.get_labels($stateParams.inventory_type, [$stateParams.view_id])
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            uniformat_payload: ['uniformat_service', (uniformat_service) => uniformat_service.get_uniformat()],
            elements_payload: [
              '$stateParams',
              'element_service',
              'user_service',
              'inventory_payload',
              ($stateParams, element_service, user_service, inventory_payload) => {
                if ($stateParams.inventory_type === 'properties') {
                  return element_service.get_elements(user_service.get_organization().id, inventory_payload.property.id);
                }
                return [];
              }
            ],
            tkbl_payload: [
              '$stateParams',
              'element_service',
              'user_service',
              'inventory_payload',
              ($stateParams, element_service, user_service, inventory_payload) => {
                if ($stateParams.inventory_type === 'properties') {
                  return element_service.get_tkbl(user_service.get_organization().id, inventory_payload.property.id);
                }
                return [];
              }
            ]
          }
        })
        .state({
          name: 'inventory_detail_cycles',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}/cycles',
          templateUrl: `${static_url}seed/partials/inventory_detail_cycles.html`,
          controller: 'inventory_detail_cycles_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                let promise;
                if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property_links(view_id);
                else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot_links(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns().then((columns) => {
                    _.remove(columns, 'related');
                    _.remove(columns, { column_name: 'lot_number', table_name: 'PropertyState' });
                    return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                  });
                }
                return inventory_service.get_taxlot_columns().then((columns) => {
                  _.remove(columns, 'related');
                  return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                });
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            profiles: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                const inventory_type = $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
                return inventory_service.get_column_list_profiles('Detail View Profile', inventory_type);
              }
            ],
            current_profile: [
              '$stateParams',
              'inventory_service',
              'profiles',
              ($stateParams, inventory_service, profiles) => {
                const validProfileIds = _.map(profiles, 'id');
                const lastProfileId = inventory_service.get_last_detail_profile($stateParams.inventory_type);
                if (_.includes(validProfileIds, lastProfileId)) {
                  return _.find(profiles, { id: lastProfileId });
                }
                const currentProfile = _.first(profiles);
                if (currentProfile) inventory_service.save_last_detail_profile(currentProfile.id, $stateParams.inventory_type);
                return currentProfile;
              }
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)]
          }
        })
        .state({
          name: 'inventory_detail_analyses',
          url: '/{inventory_type:properties}/{view_id:int}/analyses',
          templateUrl: `${static_url}seed/partials/inventory_detail_analyses.html`,
          controller: 'inventory_detail_analyses_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                let promise;
                if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property(view_id);
                else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            analyses_payload: [
              'inventory_service',
              'analyses_service',
              '$stateParams',
              'inventory_payload',
              (inventory_service, analyses_service, $stateParams, inventory_payload) => analyses_service.get_analyses_for_canonical_property(inventory_payload.property.id)
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            // users_payload: [
            //   'user_service',
            //   'organization_service',
            //   (user_service, organization_service) => organization_service.get_organization_users({ org_id: user_service.get_organization().id })
            // ],
            views_payload: [
              '$stateParams',
              'user_service',
              'inventory_service',
              'inventory_payload',
              ($stateParams, user_service, inventory_service, inventory_payload) => {
                const organization_id = user_service.get_organization().id;
                let promise;
                if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property_views(organization_id, inventory_payload.property.id);
                else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot_views(organization_id, inventory_payload.taxlot.id);

                return promise;
              }
            ],
            columns: [
              '$stateParams',
              'inventory_service',
              ($stateParams, inventory_service) => {
                if ($stateParams.inventory_type === 'properties') {
                  return inventory_service.get_property_columns().then((columns) => {
                    _.remove(columns, 'related');
                    _.remove(columns, { column_name: 'lot_number', table_name: 'PropertyState' });
                    return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                  });
                }
                return inventory_service.get_taxlot_columns().then((columns) => {
                  _.remove(columns, 'related');
                  return _.map(columns, (col) => _.omit(col, ['pinnedLeft', 'related']));
                });
              }
            ]
          }
        })
        .state({
          name: 'inventory_detail_meters',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}/meters',
          templateUrl: `${static_url}seed/partials/inventory_detail_meters.html`,
          controller: 'inventory_detail_meters_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                const promise = inventory_service.get_property(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            property_meter_usage: [
              '$stateParams',
              'user_service',
              'meter_service',
              ($stateParams, user_service, meter_service) => {
                const organization_id = user_service.get_organization().id;
                return meter_service.property_meter_usage($stateParams.view_id, organization_id, 'Exact');
              }
            ],
            meters: [
              '$stateParams',
              'user_service',
              'meter_service',
              ($stateParams, user_service, meter_service) => {
                const organization_id = user_service.get_organization().id;
                return meter_service.get_meters($stateParams.view_id, organization_id);
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)]
          }
        })
        .state({
          name: 'inventory_detail_sensors',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}/sensors',
          templateUrl: `${static_url}seed/partials/inventory_detail_sensors.html`,
          controller: 'inventory_detail_sensors_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                const promise = inventory_service.get_property(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            property_sensor_usage: [
              '$stateParams',
              'user_service',
              'sensor_service',
              ($stateParams, user_service, sensor_service) => {
                const organization_id = user_service.get_organization().id;
                return sensor_service.property_sensor_usage($stateParams.view_id, organization_id, 'Exact');
              }
            ],
            sensors: [
              '$stateParams',
              'user_service',
              'sensor_service',
              ($stateParams, user_service, sensor_service) => {
                const organization_id = user_service.get_organization().id;
                return sensor_service.get_sensors($stateParams.view_id, organization_id);
              }
            ],
            data_loggers: [
              '$stateParams',
              'user_service',
              'sensor_service',
              ($stateParams, user_service, sensor_service) => {
                const organization_id = user_service.get_organization().id;
                return sensor_service.get_data_loggers($stateParams.view_id, organization_id);
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)]
          }
        })
        .state({
          name: 'inventory_detail_timeline',
          url: '/{inventory_type:properties|taxlots}/{view_id:int}/timeline',
          templateUrl: `${static_url}seed/partials/inventory_detail_timeline.html`,
          controller: 'inventory_detail_timeline_controller',
          resolve: {
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => {
                // load `get_building` before page is loaded to avoid page flicker.
                const { view_id } = $stateParams;
                const promise = inventory_service.get_property(view_id);
                promise.catch((err) => {
                  if (err.message.match(/^(?:property|taxlot) view with id \d+ does not exist$/)) {
                    // Inventory item not found for current organization, redirecting
                    $state.go('inventory_list', { inventory_type: $stateParams.inventory_type });
                  }
                });
                return promise;
              }
            ],
            events: [
              '$stateParams',
              'event_service',
              'user_service',
              'inventory_payload',
              ($stateParams, event_service, user_service, inventory_payload) => {
                const organization_id = user_service.get_organization().id;
                const property_id = inventory_payload.property.id;
                return event_service.get_events(organization_id, $stateParams.inventory_type, property_id);
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            users_payload: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => organization_service.get_organization_users({ org_id: user_service.get_organization().id })
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)]
          }
        })
        .state({
          name: 'insights_program',
          url: '/insights',
          templateUrl: `${static_url}seed/partials/insights_program.html`,
          controller: 'insights_program_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']);
              }
            ],
            compliance_metrics: ['compliance_metric_service', (compliance_metric_service) => compliance_metric_service.get_compliance_metrics()],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            property_columns: [
              'inventory_service',
              'user_service',
              (inventory_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return inventory_service.get_property_columns_for_org(organization_id);
              }
            ],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            filter_groups: [
              '$stateParams',
              'filter_groups_service',
              ($stateParams, filter_groups_service) => {
                const inventory_type = 'Property'; // just properties for now
                return filter_groups_service.get_filter_groups(inventory_type, $stateParams.organization_id);
              }
            ]
          }
        })
        .state({
          name: 'insights_property',
          url: '/insights/property',
          templateUrl: `${static_url}seed/partials/insights_property.html`,
          controller: 'insights_property_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']);
              }
            ],
            compliance_metrics: ['compliance_metric_service', (compliance_metric_service) => compliance_metric_service.get_compliance_metrics()],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            filter_groups: [
              '$stateParams',
              'filter_groups_service',
              ($stateParams, filter_groups_service) => {
                const inventory_type = 'Property'; // just properties for now
                return filter_groups_service.get_filter_groups(inventory_type, $stateParams.organization_id);
              }
            ],
            property_columns: [
              'inventory_service',
              'user_service',
              (inventory_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return inventory_service.get_property_columns_for_org(organization_id);
              }
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            access_level_tree: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return organization_service.get_organization_access_level_tree(organization_id);
              }
            ]
          }
        })
        .state({
          name: 'custom_reports',
          url: '/insights/custom',
          templateUrl: `${static_url}seed/partials/data_view.html`,
          controller: 'data_view_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']);
              }
            ],
            valid_column_data_types: [() => ['number', 'float', 'integer', 'area', 'eui', 'ghg', 'ghg_intensity']],
            property_columns: [
              'valid_column_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_column_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_property_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_column_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            taxlot_columns: [
              'valid_column_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_column_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_taxlot_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_column_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            data_views: ['data_view_service', (data_view_service) => data_view_service.get_data_views()],
            filter_groups: [
              'filter_groups_service',
              (filter_groups_service) => {
                const inventory_type = 'Property'; // just properties for now
                return filter_groups_service.get_filter_groups(inventory_type);
              }
            ]
          }
        })
        .state({
          name: 'portfolio_summary',
          url: '/insights/portfolio_summary',
          templateUrl: `${static_url}seed/partials/portfolio_summary.html`,
          controller: 'portfolio_summary_controller',
          resolve: {
            valid_column_data_types: [() => ['number', 'float', 'integer', 'area', 'eui', 'ghg', 'ghg_intensity']],
            property_columns: [
              'valid_column_data_types',
              '$stateParams',
              'inventory_service',
              (valid_column_data_types, $stateParams, inventory_service) => inventory_service.get_property_columns_for_org($stateParams.organization_id).then((columns) => {
                _.remove(columns, { table_name: 'TaxLotState' });
                return columns;
              })
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            organization_payload: ['user_service', 'organization_service', (user_service, organization_service) => organization_service.get_organization(user_service.get_organization().id)],
            access_level_tree: [
              'organization_payload',
              'organization_service',
              (organization_payload, organization_service) => {
                const organization_id = organization_payload.organization.id;
                return organization_service.get_descendant_access_level_tree(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              'organization_payload',
              (auth_service, organization_payload) => {
                const organization_id = organization_payload.organization.id;
                return auth_service.is_authorized(organization_id, ['requires_owner']);
              }
            ]
          }
        })
        .state({
          name: 'facilities_plan',
          url: '/insights/facilities_plan',
          templateUrl: `${static_url}seed/partials/facilities_plan.html`,
          controller: 'facilities_plan_controller',
          resolve: {
            facilities_plans: ['facilities_plan_service', (facilities_plan_service) => facilities_plan_service.get_facilities_plans()],
            facilities_plan_runs: ['facilities_plan_run_service', (facilities_plan_run_service) => facilities_plan_run_service.get_facilities_plan_runs()],
            access_level_tree: [
              'organization_service',
              'user_service',
              (organization_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return organization_service.get_organization_access_level_tree(organization_id);
              }
            ],
            property_columns: [
              'inventory_service',
              'user_service',
              (inventory_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return inventory_service.get_property_columns_for_org(organization_id);
              }
            ],
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']);
              }
            ]
          }
        })
        .state({
          name: 'data_view',
          url: '/insights/custom/{id:int}',
          templateUrl: `${static_url}seed/partials/data_view.html`,
          controller: 'data_view_controller',
          resolve: {
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']);
              }
            ],
            valid_column_data_types: [() => ['number', 'float', 'integer', 'area', 'eui', 'ghg', 'ghg_intensity']],
            property_columns: [
              'valid_column_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_column_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_property_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_column_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            taxlot_columns: [
              'valid_column_data_types',
              '$stateParams',
              'inventory_service',
              'naturalSort',
              (valid_column_data_types, $stateParams, inventory_service, naturalSort) => inventory_service.get_taxlot_columns_for_org($stateParams.organization_id).then((columns) => {
                columns = _.reject(columns, (item) => item.related || !valid_column_data_types.includes(item.data_type)).sort((a, b) => naturalSort(a.displayName, b.displayName));
                return columns;
              })
            ],
            cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
            data_views: ['data_view_service', (data_view_service) => data_view_service.get_data_views()],
            filter_groups: [
              'filter_groups_service',
              (filter_groups_service) => {
                const inventory_type = 'Property'; // just properties for now
                return filter_groups_service.get_filter_groups(inventory_type);
              }
            ]
          }
        });
    }
  ]);

  SEED_app.config([
    '$httpProvider',
    ($httpProvider) => {
      $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
      $httpProvider.defaults.paramSerializer = 'httpParamSerializerSeed';
    }
  ]);

  /**
   * Disable Angular debugging based on Django DEBUG flag.
   */
  SEED_app.config([
    '$compileProvider',
    ($compileProvider) => {
      $compileProvider.debugInfoEnabled(window.SEED.debug);
      $compileProvider.commentDirectivesEnabled(false);
      // $compileProvider.cssClassDirectivesEnabled(false); // This cannot be enabled due to the draggable ui-grid rows
    }
  ]);

  SEED_app.config([
    '$translateProvider',
    ($translateProvider) => {
      // Log un-translated strings when running in debug mode
      // if (window.SEED.debug) {
      //   $translateProvider.useMissingTranslationHandlerLog();
      // }

      $translateProvider
        .useStaticFilesLoader({
          prefix: '/static/seed/locales/',
          suffix: '.json'
        })
        .registerAvailableLanguageKeys(['en_US', 'es', 'fr_CA'], {
          en: 'en_US',
          es: 'es',
          fr: 'fr_CA',
          'en_*': 'en_US',
          'es_*': 'es',
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
    }
  ]);

  /**
   * creates the object 'urls' which can be injected into a service, controller, etc.
   */
  SEED_app.constant('urls', {
    seed_home: SEED.urls.seed_home,
    static_url: SEED.urls.STATIC_URL
  });

  /**
   * @param {string} a
   * @param {string} b
   */
  const numericComparison = (a, b) => {
    const numA = Number(a);
    if (Number.isNaN(numA)) return false;
    const numB = Number(b);
    if (Number.isNaN(numB)) return false;
    if (numA === numB) return 0;
    return numA < numB ? -1 : 1;
  };
  const { compare } = new Intl.Collator(undefined, { ignorePunctuation: true, numeric: true, sensitivity: 'base' });
  /**
   * @param {string} [a] - The first string for comparison
   * @param {string} [b] - The second string for comparison
   * @returns {number} Sort result
   */
  const naturalSort = (a, b) => {
    if (a === b) return 0;
    if (!a) return 1;
    if (!b) return -1;

    const numericResult = numericComparison(a, b);
    if (numericResult !== false) return numericResult;

    return compare(a, b);
  };
  SEED_app.constant('naturalSort', naturalSort);
})();
