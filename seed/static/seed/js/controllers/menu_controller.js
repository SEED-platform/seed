/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.menu', []).controller('menu_controller', [
  '$rootScope',
  '$scope',
  '$location',
  '$window',
  '$uibModal',
  '$log',
  'urls',
  'auth_service',
  'organization_service',
  'user_service',
  'dataset_service',
  'modified_service',
  'inventory_service',
  '$timeout',
  '$state',
  // eslint-disable-next-line func-names
  function ($rootScope, $scope, $location, $window, $uibModal, $log, urls, auth_service, organization_service, user_service, dataset_service, modified_service, inventory_service, $timeout, $state) {
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

    $scope.hide_load_error = () => {
      $rootScope.route_load_error = false;
    };
    $scope.$on('app_error', (event, data) => {
      // Keep the first error
      if (!$rootScope.route_load_error) {
        $rootScope.route_load_error = true;
        $scope.menu.error_message = data.message;
        $rootScope.load_error_message = data.data.message;
      }
    });
    $scope.$on('app_success', () => {
      $rootScope.route_load_error = false;
    });
    $scope.$on('organization_list_updated', () => {
      init();
    });
    $scope.is_active = (menu_item, use_pathname) => {
      let current_path = $location.path();
      if (use_pathname) {
        current_path = $window.location.pathname;
      }

      if (menu_item === current_path) {
        return true;
      }
      return menu_item !== '/' && current_path.startsWith(menu_item);
    };

    $scope.href = (url) => {
      window.location = url;
    };

    // Sets initial expanded/collapse state of sidebar menu
    const STORAGE_KEY = 'seed_nav_is_expanded';

    function init_menu() {
      if ($window.localStorage.getItem(STORAGE_KEY) === null) {
        $window.localStorage.setItem(STORAGE_KEY, 'true');
      }
      const isNavExpanded = $window.localStorage.getItem(STORAGE_KEY) === 'true';
      $scope.expanded_controller = isNavExpanded;
      $scope.collapsed_controller = !isNavExpanded;
      $scope.narrow_controller = isNavExpanded;
      $scope.wide_controller = !isNavExpanded;
    }

    // returns true if menu toggle has never been clicked, i.e., first run, else returns false
    $scope.menu_toggle_has_never_been_clicked = () => $scope.expanded_controller === $scope.collapsed_controller;

    $scope.is_initial_state = () => $scope.menu_toggle_has_never_been_clicked();

    // expands and collapses the sidebar menu
    $scope.toggle_menu = () => {
      $scope.is_initial_state = false; // we can now turn on animations
      $scope.expanded_controller = !$scope.expanded_controller;
      $scope.collapsed_controller = !$scope.collapsed_controller;
      $scope.narrow_controller = !$scope.narrow_controller;
      $scope.wide_controller = !$scope.wide_controller;
      try {
        // TODO : refactor to put() when we move to Angular 1.3 or greater
        $window.localStorage.setItem(STORAGE_KEY, $scope.expanded_controller.toString());
      } catch (err) {
        // it's ok if the cookie can't be written, so just report in the log and move along.
        $log.error("Couldn't write cookie for nav state. Error: ", err);
      }
    };

    /**
     * open_data_upload_modal: opens the data upload modal, passes in the
     *  data_upload_modal_controller controller.
     */
    $scope.open_data_upload_modal = () => {
      const dataModalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/data_upload_modal.html`,
        controller: 'data_upload_modal_controller',
        resolve: {
          cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
          step: () => 1,
          dataset: () => ({}),
          organization: () => $scope.menu.user.organization
        }
      });

      dataModalInstance.result.finally(() => {
        $scope.$broadcast('datasets_updated');
        init();
      });
    };

    /**
     * open_sample_data_modal: opens the auto-populate sample data modal
     */
    $scope.open_sample_data_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/sample_data_modal.html`,
        controller: 'sample_data_modal_controller',
        size: 'md',
        resolve: {
          organization: () => $scope.menu.user.organization,
          cycle: [
            'Notification',
            'organization_service',
            (Notification, organization_service) => organization_service.get_organization($scope.menu.user.organization.org_id).then((response) => {
              if (!response.organization.cycles.length) {
                Notification.error('Error: please create a cycle before Auto-Populating data');
                return;
              }
              const lastCycleId = inventory_service.get_last_cycle();
              let lastCycle;
              if (typeof lastCycleId === 'number') {
                lastCycle = response.organization.cycles.find((cycle) => cycle.cycle_id === lastCycleId);
              }
              if (lastCycleId === undefined || !lastCycle) {
                lastCycle = response.organization.cycles[0];
              }
              return lastCycle;
            })
          ],
          profiles: ['inventory_service', (inventory_service) => inventory_service.get_column_list_profiles('List View Profile', 'Property')]
        }
      });
    };

    /**
     * sets the users primary organization, reloads/refreshed the page
     * @param {obj} org
     */
    $scope.set_user_org = (org) => {
      $scope.mouseout_org();
      user_service.set_organization(org);
      $scope.menu.user.organization = org;
      console.log($scope.menu.user.organization);
      $state.reload();
      init();
    };
    // set authorization and organization data to $scope
    const set_auth = (org_id) => {
      auth_service.is_authorized(org_id, ['requires_owner']).then(
        (data) => {
          $scope.auth = data.auth.requires_owner ? data.auth : 'not authorized';
        },
        (data) => {
          $scope.auth = data.message;
        }
      );
    };
    $scope.mouseover_org = (org_id) => {
      $scope.show_org_id = true;
      $scope.hover_org_id = org_id;
    };
    $scope.mouseout_org = () => {
      $scope.show_org_id = false;
    };
    $scope.track_mouse = (e) => {
      const xpos = `${e.view.window.innerWidth - e.clientX - 105}px`;
      const ypos = `${e.clientY - 25}px`;
      $scope.hover_style = `right: ${xpos}; top: ${ypos};`;
    };

    // DMcQ: Set up watch statements to keep nav updated with latest datasets_count, etc.
    //      This isn't the best solution but most expedient. This approach should be refactored later by
    //      a proper strategy of binding views straight to model properties.
    //      See my comments here: https://github.com/SEED-platform/seed/issues/44

    // watch datasets
    $scope.$watch(
      () => dataset_service.total_datasets_for_user,
      (data) => {
        $scope.datasets_count = data;
      },
      true
    );

    // watch organizations
    $scope.$watch(
      () => organization_service.total_organizations_for_user,
      (data) => {
        $scope.organizations_count = data;
      },
      true
    );

    var init = () => {
      if (!$scope.logged_in) {
        return;
      }
      if (!user_service.get_organization().id) {
        $uibModal.open({
          backdrop: 'static',
          keyboard: false,
          templateUrl: `${urls.static_url}seed/partials/create_organization_modal.html`,
          controller: 'create_organization_modal_controller',
          resolve: {
            user_id: user_service.get_user_id()
          }
        });
      } else {
        organization_service
          .get_organizations_brief()
          .then((data) => {
            $scope.organizations_count = data.organizations.length;
            $scope.menu.user.organizations = data.organizations;
            // get the default org for the user
            $scope.menu.user.organization = _.find(data.organizations, { id: _.toInteger(user_service.get_organization().id) });
            set_auth($scope.menu.user.organization.id);
          })
          .catch((error) => {
            // user does not have an org
            $rootScope.route_load_error = true;
            $rootScope.load_error_message = error.data.message;
          });
        dataset_service.get_datasets_count().then((data) => {
          $scope.datasets_count = data.datasets_count;
        });
      }
    };

    if ($location.search().http_error) {
      $scope.http_error = $location.search().http_error;
    }

    $scope.closeAlert = () => {
      $scope.http_error = false;
    };

    init();
    init_menu();
  }
]);
