/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.menu', [])
  .controller('menu_controller', [
    '$rootScope',
    '$scope',
    '$location',
    '$window',
    '$uibModal',
    '$log',
    'urls',
    'organization_service',
    'user_service',
    'dataset_service',
    'modified_service',
    'inventory_service',
    '$timeout',
    '$state',
    function (
      $rootScope,
      $scope,
      $location,
      $window,
      $uibModal,
      $log,
      urls,
      organization_service,
      user_service,
      dataset_service,
      modified_service,
      inventory_service,
      $timeout,
      $state
    ) {
      // initial state of css classes for menu and sidebar
      $scope.expanded_controller = false;
      $scope.collapsed_controller = false;
      $scope.narrow_controller = false;
      $scope.wide_controller = false;
      $scope.username = window.BE.username;
      $scope.logged_in = $scope.username.length > 0;
      $scope.urls = urls;
      $scope.datasets_count = 0;
      $scope.organizations_count = 0;
      $scope.menu = {
        user: {}
      };
      $scope.is_initial_state = $scope.expanded_controller === $scope.collapsed_controller;

      $scope.hide_load_error = function () {
        $rootScope.route_load_error = false;
      };
      $scope.$on('app_error', function (event, data) {
        // Keep the first error
        if (!$rootScope.route_load_error) {
          $rootScope.route_load_error = true;
          $scope.menu.error_message = data.message;
          $rootScope.load_error_message = data.data.message;
        }
      });
      $scope.$on('app_success', function () {
        $rootScope.route_load_error = false;
      });
      $scope.$on('organization_list_updated', function () {
        init();
      });
      $scope.is_active = function (menu_item, use_pathname) {
        var current_path = $location.path();
        if (use_pathname) {
          current_path = $window.location.pathname;
        }

        if (menu_item === current_path) {
          return true;
        } else {
          return menu_item !== '/' && _.startsWith(current_path, menu_item);
        }
      };

      $scope.href = function (url) {
        window.location = url;
      };

      //Sets initial expanded/collapse state of sidebar menu
      const STORAGE_KEY = "seed_nav_is_expanded";

      function init_menu() {
        if ($window.localStorage.getItem(STORAGE_KEY) === null) {
          $window.localStorage.setItem(STORAGE_KEY, 'true');
        }
        var isNavExpanded = $window.localStorage.getItem(STORAGE_KEY) === 'true';
        $scope.expanded_controller = isNavExpanded;
        $scope.collapsed_controller = !isNavExpanded;
        $scope.narrow_controller = isNavExpanded;
        $scope.wide_controller = !isNavExpanded;
      }

      // returns true if menu toggle has never been clicked, i.e. first run, else returns false
      $scope.menu_toggle_has_never_been_clicked = function () {
        return $scope.expanded_controller === $scope.collapsed_controller;
      };

      $scope.is_initial_state = function () {
        return $scope.menu_toggle_has_never_been_clicked();
      };

      // expands and collapses the sidebar menu
      $scope.toggle_menu = function () {
        $scope.is_initial_state = false; //we can now turn on animations
        $scope.expanded_controller = !$scope.expanded_controller;
        $scope.collapsed_controller = !$scope.collapsed_controller;
        $scope.narrow_controller = !$scope.narrow_controller;
        $scope.wide_controller = !$scope.wide_controller;
        try {
          //TODO : refactor to put() when we move to Angular 1.3 or greater
          $window.localStorage.setItem(STORAGE_KEY, $scope.expanded_controller.toString());
        } catch (err) {
          //it's ok if the cookie can't be written, so just report in the log and move along.
          $log.error('Couldn\'t write cookie for nav state. Error: ', err);
        }
      };

      /**
       * open_data_upload_modal: opens the data upload modal, passes in the
       *  data_upload_modal_controller controller.
       */
      $scope.open_data_upload_modal = function () {
        var dataModalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/data_upload_modal.html',
          controller: 'data_upload_modal_controller',
          resolve: {
            cycles: ['cycle_service', function (cycle_service) {
              return cycle_service.get_cycles();
            }],
            step: _.constant(1),
            dataset: function () {
              return {};
            },
            organization: function () {
              return $scope.menu.user.organization;
            }
          }
        });

        dataModalInstance.result.finally(function () {
          $scope.$broadcast('datasets_updated');
          init();
        });
      };

      /**
       * open_sample_data_modal: opens the auto-populate sample data modal
       */
      $scope.open_sample_data_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/sample_data_modal.html',
          controller: 'sample_data_modal_controller',
          size: 'md',
          resolve: {
            organization: () => {
              return $scope.menu.user.organization;
            },
            cycle: ['Notification', 'organization_service', function (Notification, organization_service) {
              return organization_service.get_organization($scope.menu.user.organization.org_id)
                .then(response => {
                  if (!response.organization.cycles.length) {
                    Notification.error('Error: please create a cycle before Auto-Populating data');
                    return;
                  }
                  let lastCycleId = inventory_service.get_last_cycle();
                  let lastCycle;
                  if (typeof lastCycleId === 'number') {
                    lastCycle = response.organization.cycles.find(cycle => cycle.cycle_id === lastCycleId)
                  }
                  if ((lastCycleId === undefined || !lastCycle)) {
                    lastCycle = response.organization.cycles[0];
                  }
                  return lastCycle;
                });
            }],
            profiles: ['inventory_service', function (inventory_service) {
              return inventory_service.get_column_list_profiles('List View Profile', 'Property');
            }]
          }
        });
      };

      /**
       * sets the users primary organization, reloads/refreshed the page
       * @param {obj} org
       */
      $scope.set_user_org = function (org) {
        user_service.set_organization(org);
        $scope.menu.user.organization = org;
        console.log($scope.menu.user.organization);
        $state.reload();
        init();
      };

      //DMcQ: Set up watch statements to keep nav updated with latest datasets_count, etc.
      //      This isn't the best solution but most expedient. This approach should be refactored later by
      //      a proper strategy of binding views straight to model properties.
      //      See my comments here: https://github.com/SEED-platform/seed/issues/44

      //watch datasets
      $scope.$watch(function () {
        return dataset_service.total_datasets_for_user;
      }, function (data) {
        $scope.datasets_count = data;
      }, true);

      //watch organizations
      $scope.$watch(function () {
        return organization_service.total_organizations_for_user;
      }, function (data) {
        $scope.organizations_count = data;
      }, true);

      var init = function () {
        if (!$scope.logged_in) {
          return;
        }
        if (!user_service.get_organization().id) {
          $uibModal.open({
            backdrop: 'static',
            keyboard: false,
            templateUrl: urls.static_url + 'seed/partials/create_organization_modal.html',
            controller: 'create_organization_modal_controller',
            resolve: {
              user_id: user_service.get_user_id()
            }
          });
        } else {
          organization_service.get_organizations_brief().then(function (data) {
            $scope.organizations_count = data.organizations.length;
            $scope.menu.user.organizations = data.organizations;
            // get the default org for the user
            $scope.menu.user.organization = _.find(data.organizations, {id: _.toInteger(user_service.get_organization().id)});
          }).catch(function (error) {
            // user does not have an org
            $rootScope.route_load_error = true;
            $rootScope.load_error_message = error.data.message;
          });
          dataset_service.get_datasets_count().then(function (data) {
            $scope.datasets_count = data.datasets_count;
          });
        }
      };
      init();
      init_menu();
    }]);
