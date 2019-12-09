/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
    '$timeout',
    '$state',
    '$cookies',
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
      $timeout,
      $state,
      $cookies
    ) {
      // initial state of css classes for menu and sidebar
      $scope.expanded_controller = false;
      $scope.collapsed_controller = false;
      $scope.narrow_controller = false;
      $scope.wide_controller = false;
      $scope.username = window.BE.username;
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
        }
      });
      $scope.$on('organization_list_updated', function () {
        init();
      });

      $scope.is_active = function (menu_item) {
        if (menu_item === $location.path()) {
          return true;
        } else if (menu_item !== '/' && _.startsWith($location.path(), menu_item)) {
          return true;
        } else if (menu_item === '/seed/data' && !_.includes($location.absUrl(), '#')) {
          if (_.includes($location.absUrl(), menu_item)) return true;
          if (_.includes($location.absUrl(), 'worksheet')) return true;
          if (_.includes($location.absUrl(), 'mapping')) return true;
          if (_.includes($location.absUrl(), 'cleaning')) return true;
          if (_.includes($location.absUrl(), 'merge')) return true;
          if (_.includes($location.absUrl(), 'import')) return true;
          return false;
        } else {
          return false;
        }
      };

      $scope.href = function (url) {
        window.location = url;
      };

      //Sets initial expanded/collapse state of sidebar menu
      function init_menu () {
        //Default to false but use cookie value if one has been set
        var isNavExpanded = $cookies.seed_nav_is_expanded === 'true';
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
          $cookies.seed_nav_is_expanded = $scope.expanded_controller.toString();
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
       * sets the users primary organization, reloads/refreshed the page
       * @param {obj} org
       */
      $scope.set_user_org = function (org) {
        user_service.set_organization(org);
        $scope.menu.user.organization = org;
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
        organization_service.get_organizations_brief().then(function (data) {
          $scope.organizations_count = data.organizations.length;
          $scope.menu.user.organizations = data.organizations;

          // get the default org for the user
          $scope.menu.user.organization = _.find(data.organizations, {id: _.toInteger(user_service.get_organization().id)});
        }).catch(function (error) {
          $rootScope.route_load_error = true;
          $rootScope.load_error_message = error.data.message;
        });

        dataset_service.get_datasets_count().then(function (data) {
          $scope.datasets_count = data.datasets_count;
        });
      };
      init();
      init_menu();
    }]);
