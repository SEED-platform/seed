/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
    'project_service',
    'organization_service',
    'user_service',
    'dataset_service',
    '$timeout',
    '$state',
    '$cookies',
    'spinner_utility',
    function ($rootScope,
              $scope,
              $location,
              $window,
              $uibModal,
              $log,
              urls,
              project_service,
              organization_service,
              user_service,
              dataset_service,
              $timeout,
              $state,
              $cookies,
              spinner_utility) {

      // initial state of css classes for menu and sidebar
      $scope.expanded_controller = false;
      $scope.collapsed_controller = false;
      $scope.narrow_controller = false;
      $scope.wide_controller = false;
      $scope.username = window.BE.username;
      $scope.urls = urls;
      $scope.datasets_count = 0;
      $scope.projects_count = 0;
      $scope.search_input = '';
      $scope.organizations_count = 0;
      $scope.menu = {};
      $scope.menu.project = {};
      $scope.menu.create_project_state = 'create';
      $scope.menu.create_project_error = false;
      $scope.menu.create_project_error_message = '';
      $scope.saving_indicator = false;
      $scope.menu.loading = false;
      $scope.menu.route_load_error = false;
      $scope.menu.user = {};
      $scope.is_initial_state = $scope.expanded_controller === $scope.collapsed_controller;

      $rootScope.$on('$stateChangeError', function (event, toState, toParams, fromState, fromParams, error) {
        $scope.menu.loading = false;
        $scope.menu.route_load_error = true;
        $log.error(error);
        if (error === 'not authorized' || error === 'Your page could not be located!') {
          $scope.menu.error_message = error;
        }
        spinner_utility.hide();
      });
      $rootScope.$on('$stateChangeStart', function (event, toState) {
        $scope.menu.loading = toState.controller === 'mapping_controller';
        spinner_utility.show();
      });
      $rootScope.$on('$stateChangeSuccess', function () {
        $scope.menu.loading = false;
        $scope.menu.route_load_error = false;
        spinner_utility.hide();
      });
      $rootScope.$on('$stateNotFound', function (event, unfoundState) {
        $log.error('State not found:', unfoundState.to);
      });
      $scope.$on('app_error', function (event, data) {
        $scope.menu.route_load_error = true;
        $scope.menu.error_message = data.message;
      });
      //commented out 6.15.17 dbressan code cov
      // $scope.$on('project_created', function () {
      //   init();
      // });
      $scope.$on('show_saving', function () {
        $scope.saving_indicator = true;
        start_saving_indicator('. . .   ', '');
      });
      $scope.$on('finished_saving', function () {
        $scope.saving_indicator = false;
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

      $scope.reset_search_field = function () {
        $scope.search_input = '';
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

      //commented out 6.15.17 dbressan code cov
      // $scope.open_create_project_modal = function () {
      //   var modalInstance = $uibModal.open({
      //     templateUrl: urls.static_url + 'seed/partials/edit_project_modal.html',
      //     controller: 'edit_project_modal_controller',
      //     resolve: {
      //       project: function () {
      //         return $scope.menu.project;
      //       },
      //       create_project: _.constant(true)
      //     }
      //   });
      //
      //   modalInstance.result.then(
      //     function (project) {
      //       $log.info(project);
      //       init();
      //       $scope.$broadcast('projects_updated');
      //     }, function (message) {
      //     $log.info(message);
      //     $log.info('Modal dismissed at: ' + new Date());
      //   });
      // };

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

        dataModalInstance.result.then(function () {
          $scope.$broadcast('datasets_updated');
          init();
        }, function () {
          $scope.$broadcast('datasets_updated');
          init();
        });
      };

      /**
       * start_saving_indicator: 'speaks' through a chuck of text. Used as a saving
       *              indicator. $scope.saving_indicator should be set to true
       *              for this to run.
       *
       *  TODO(Aleck): break out into a directive or service and make functional
       *               where the element is a param, as is the bool, and timing
       *
       *  e.g. start_saving_indicator(". . .  ", "") will update the DOM element with
       *       class=saving_progress as follows:
       *       After 250ms: "."
       *       After 250ms: ". "
       *       After 250ms: ".  ."
       *       After 250ms: ".  . "
       *       After 250ms: ".  .  ."
       *       After 250ms: ".  .  . "
       *       After 250ms: ""
       *       After 250ms: "."
       *       After 250ms: ". "
       *
       *  @params {string} full_text: indicator text to iterate and loop through
       *  @params {string} partial: the substring of the full_text displayed
       *  @local {bool} $scope.saving_indicator true to continue
       */
      var start_saving_indicator = function (full_text, partial) {
        var delay_ms = 250;
        angular.element('.saving_progress').html(partial);
        if (!$scope.saving_indicator) {
          return;
        }
        if (full_text === partial) {
          start_saving_indicator(full_text, '');
        } else {
          $timeout(function () {
            start_saving_indicator(full_text, full_text.substring(0, partial.length + 1));
          }, delay_ms);
        }
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

      //watch projects
      $scope.$watch(function () {
        return project_service.total_number_projects_for_user;
      }, function (data) {
        $scope.projects_count = data;
      }, true);

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
        });

        project_service.get_datasets_count().then(function (data) {
          $scope.datasets_count = data.datasets_count;
        });

        // project_service.get_projects_count().then(function (data) {
        //   // resolve promise
        //   $scope.projects_count = data.projects_count;
        // });
      };
      init();
      init_menu();
    }]);
