/*
 * :copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.menu', [])
.controller('seed_menu_controller', [
  '$scope',
  '$http',
  '$location',
  '$window',
  '$uibModal',
  '$log',
  'urls',
  'building_services',
  'project_service',
  'uploader_service',
  'organization_service',
  'user_service',
  'dataset_service',
  '$timeout',
  '$route',
  '$cookies',
  function(
    $scope,
    $http,
    $location,
    $window,
    $uibModal,
    $log,
    urls,
    building_services,
    project_service,
    uploader_service,
    organization_service,
    user_service,
    dataset_service,
    $timeout,
    $route,
    $cookies) {

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
    $scope.organizations_count = 0;
    $scope.menu = {};
    $scope.menu.project = {};
    $scope.menu.create_project_state = "create";
    $scope.menu.create_project_error = false;
    $scope.menu.create_project_error_message = "";
    $scope.saving_indicator = false;
    $scope.menu.loading = false;
    $scope.menu.route_load_error = false;
    $scope.menu.user = {};
    $scope.is_initial_state = $scope.expanded_controller === $scope.collapsed_controller;

    $scope.$on("$routeChangeError", function(event, current, previous, rejection) {
	   $scope.menu.loading = false;
        $scope.menu.route_load_error = true;
        if (rejection === "not authorized" || rejection === "Your page could not be located!") {
            $scope.menu.error_message = rejection;
        }
    });
    $scope.$on("$routeChangeStart", function($event, next, current) {
        $scope.menu.loading = next.controller === "mapping_controller";
    });
    $scope.$on("$routeChangeSuccess", function() {
	$scope.menu.loading = false;
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

    //Sets initial expanded/collapse state of sidebar menu
    function init_menu(){
        //Default to false but use cookie value if one has been set
        var isNavExpanded = $cookies.seed_nav_is_expanded === "true";
        $scope.expanded_controller = isNavExpanded;
        $scope.collapsed_controller = !isNavExpanded;
        $scope.narrow_controller = isNavExpanded;
        $scope.wide_controller = !isNavExpanded; 
    }

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
        $scope.is_initial_state = false; //we can now turn on animations
        $scope.expanded_controller = !$scope.expanded_controller;
        $scope.collapsed_controller = !$scope.collapsed_controller;
        $scope.narrow_controller = !$scope.narrow_controller;
        $scope.wide_controller = !$scope.wide_controller;   
        try{
            //TODO : refactor to put() when we move to Angular 1.3 or greater
            $cookies.seed_nav_is_expanded = $scope.expanded_controller.toString(); 
        }
        catch(err){
            //it's ok if the cookie can't be written, so just report in the log and move along.
            $log.error("Couldn't write cookie for nav state. Error: ", err);
        }
    };

    $scope.open_create_project_modal = function() {
        var modalInstance = $uibModal.open({
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
        var dataModalInstance = $uibModal.open({
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

    //DMcQ: Set up watch statements to keep nav updated with latest buildings_count, datasets_count, etc. 
    //      This isn't the best solution but most expedient. This approach should be refactored later by
    //      a proper strategy of binding views straight to model properties.
    //      See my comments here: https://github.com/SEED-platform/seed/issues/44
    
    //watch projects
    $scope.$watch(  function () { return project_service.total_number_projects_for_user; }, 
                    function (data) {
                        $scope.projects_count = data;
                    }, 
                    true
                );

    //watch buildings
    $scope.$watch(  function () { return building_services.total_number_of_buildings_for_user; }, 
                    function (data) {
                        $scope.buildings_count = data;
                    }, 
                    true
                );
    
    //watch datasets
    $scope.$watch(  function () { return dataset_service.total_datasets_for_user; }, 
                    function (data) {
                        $scope.datasets_count = data;
                    }, 
                    true
                );        

    //watch organizations
    $scope.$watch(  function () { return organization_service.total_organizations_for_user; }, 
                    function (data) {
                        $scope.organizations_count = data; 
                    }, 
                    true
                );

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
            $scope.organizations_count = data.organizations.length;
            $scope.menu.user.organizations = data.organizations;
        });
    };
    init();
    init_menu();
}]);
