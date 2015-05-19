/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.menu', [])
.controller('seed_menu_controller', [
  '$scope',
  '$http',
  '$location',
  '$window',
  '$modal',
  '$log',
  'urls',
  'building_services',
  'project_service',
  'uploader_service',
  'organization_service',
  'user_service',
  '$timeout',
  '$route',
  function(
    $scope,
    $http,
    $location,
    $window,
    $modal,
    $log,
    urls,
    building_services,
    project_service,
    uploader_service,
    organization_service,
    user_service,
    $timeout,
    $route) {

    // initial state of css classes for menu and sidebar
    $scope.expanded_controller = false;
    $scope.collapsed_controller = false;
    $scope.narrow_controller = false;
    $scope.wide_controller = false;
    $scope.username = window.BE.username;
    $scope.urls = urls;
    $scope.buildings_count = 0;
    $scope.datasets_count = 0;
    $scope.projects_count = 0;
    $scope.search_input = "";
    $scope.menu = {};
    $scope.menu.project = {};
    $scope.menu.create_project_state = "create";
    $scope.menu.create_project_error = false;
    $scope.menu.create_project_error_message = "";
    $scope.saving_indicator = false;
    $scope.menu.route_load_error = false;
    $scope.menu.user = {};

    $scope.$on("$routeChangeError", function(event, current, previous, rejection) {
        $scope.menu.route_load_error = true;
        if (rejection === "not authorized" || rejection === "Your page could not be located!") {
            $scope.menu.error_message = rejection;
        }
    });
    $scope.$on("$routeChangeStart", function($event, next, current) {
        $scope.menu.loading = next.controller === "mapping_controller";
    });
    $scope.$on("$routeChangeSuccess", function() {
        $scope.menu.route_load_error = false;
    });
    $scope.$on('app_error', function(event, data){
        $scope.menu.route_load_error = true;
        $scope.menu.error_message = data.message;
    });
    $scope.$on('project_created', function(event, data) {
        init();
    });
    $scope.$on('show_saving', function(event, data) {
        $scope.saving_indicator = true;
        start_saving_indicator(". . .   ", "");
    });
    $scope.$on('finished_saving', function(event, data) {
        $scope.saving_indicator = false;
    });

    $scope.input_search = function() {
        if ($location.absUrl().indexOf("#") === -1) {
            // not on SEED angularjs route managed page
            $window.location.href = urls.seed_home + "#/buildings?q=" + $scope.search_input;
        } else {
            $location.path('/buildings').search('q=' + $scope.search_input);
        }
    };


    $scope.is_active = function(menu_item) {
        if (menu_item === $location.path()) {
            return true;
        } else if (menu_item !== "/" && $location.path().indexOf(menu_item) === 0) {
            return true;
        } else if (menu_item === '/seed/data' && $location.absUrl().indexOf('#') === -1) {
            if ($location.absUrl().indexOf(menu_item) !== -1) {
                return true;
            }
            if ($location.absUrl().indexOf('worksheet') !== -1) {
                return true;
            }
            if ($location.absUrl().indexOf('mapping') !== -1) {
                return true;
            }
            if ($location.absUrl().indexOf('cleaning') !== -1) {
                return true;
            }
            if ($location.absUrl().indexOf('merge') !== -1) {
                return true;
            }
            if ($location.absUrl().indexOf('import') !== -1) {
                return true;
            }
            return false;
        }
        else {
            return false;
        }
    };

    $scope.href = function(url) {
        window.location = url;
    };

    $scope.reset_search_field = function() {
        $scope.search_input = "";
    };


    // returns true if menu toggle has never been clicked, i.e. first run, else returns false
    $scope.menu_toggle_has_never_been_clicked = function () {
        if ($scope.expanded_controller === $scope.collapsed_controller) {
            return true;
        } else {
            return false;
        }
    };

    $scope.is_initial_state = function() {
        return $scope.menu_toggle_has_never_been_clicked();
    };

    // expands and collapses the sidebar menu
    $scope.toggle_menu = function() {
        if ($scope.menu_toggle_has_never_been_clicked()) {
            $scope.expanded_controller = true;
            $scope.collapsed_controller = false;
            $scope.narrow_controller = true;
            $scope.wide_controller = false;
        }
        else {
            $scope.expanded_controller = !$scope.expanded_controller;
            $scope.collapsed_controller = !$scope.collapsed_controller;
            $scope.narrow_controller = !$scope.narrow_controller;
            $scope.wide_controller = !$scope.wide_controller;
        }
    };

    $scope.open_create_project_modal = function() {
        var modalInstance = $modal.open({
            templateUrl: urls.static_url + 'seed/partials/edit_project_modal.html',
            controller: 'edit_project_modal_ctrl',
            resolve: {
                project: function () {
                    return $scope.menu.project;
                },
                create_project: function () {
                    return true;
                }
            }
        });

        modalInstance.result.then(
            function (project) {
                $log.info(project);
                init();
                $scope.$broadcast('projects_updated');
        }, function (message) {
                $log.info(message);
                $log.info('Modal dismissed at: ' + new Date());
        });
    };

    /**
     * open_data_upload_modal: opens the data upload modal, passes in the 
     *  data_upload_modal_ctrl controller. 
     */
    $scope.open_data_upload_modal = function() {
        var dataModalInstance = $modal.open({
            templateUrl: urls.static_url + 'seed/partials/data_upload_modal.html',
            controller: 'data_upload_modal_ctrl',
            resolve: {
                step: function(){
                    return 1;
                },
                dataset: function(){
                    return {};
                }
            }
        });

        dataModalInstance.result.then(
            // modal close() function
            function () {
                $scope.$broadcast('datasets_updated');
                init();
            // modal dismiss() function
        }, function (message) {
                // dismiss
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
    var start_saving_indicator = function(full_text, partial) {
        var delay_ms = 250;
        angular.element(".saving_progress").html(partial);
        if (!$scope.saving_indicator) {
            return;
        }
        if (full_text === partial){
            start_saving_indicator(full_text, "");
        } else {
            $timeout(function(){
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
        $route.reload();
        init();
    };

    var init = function() {
        // get the default org for the user
        $scope.menu.user.organization = user_service.get_organization();
        building_services.get_total_number_of_buildings_for_user().then(function(data) {
            // resolve promise
            $scope.buildings_count = data.buildings_count;
        });
        project_service.get_datasets_count().then(function(data) {
            // resolve promise
            $scope.datasets_count = data.datasets_count;
        });
        project_service.get_projects_count().then(function(data) {
            // resolve promise
            $scope.projects_count = data.projects_count;
        });
        organization_service.get_organizations().then(function (data) {
            // resolve promise
            $scope.menu.user.organizations = data.organizations;
        });
    };
    init();
}]);
