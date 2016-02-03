/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.building_list', [])
.controller('building_list_controller', [
  '$scope',
  '$routeParams',
  '$timeout',
  '$http',
  '$log',
  '$uibModal',
  '$location',
  'building_services',
  'project_service',
  'urls',
  'user_service',
  'search_payload',
  'default_columns',
  'all_columns',
  'project_payload',
  'search_service',
  'label_service',
  function(
    $scope,
    $routeParams,
    $timeout,
    $http,
    $log,
    $uibModal,
    $location,
    building_services,
    project_service,
    urls,
    user_service,
    search_payload,
    default_columns,
    all_columns,
    project_payload,
    search_service,
    label_service
  ) {
    // extend the search_service
    $scope.search = angular.copy(search_service);
    $scope.search.url = urls.search_buildings;

    $scope.user = {};
    $scope.user.project_id = $routeParams.project_id;
    $scope.columns = [];
    $scope.labels = [];
    $scope.selected_labels = [];
    $scope.is_loading = false;
    $scope.project = project_payload.project;
    $scope.show_alert = false;
    $scope.progress_percentage = 0;
    $scope.create_project_state = 'create';
    $scope.custom_view = {};
    $scope.custom_view_columns = [];
    $scope.urls = urls;
    $scope.assessor_fields = [];
    $scope.create_project_error = false;
    $scope.create_project_error_message = "";
    $scope.selected_existing_project = null;

    // Matching dropdown values
    var SHOW_ALL = "Show All";
    var SHOW_MATCHED = "Show Matched";
    var SHOW_UNMATCHED = "Show Unmatched";

    /**
    * SEARCH CODE
    */

    /* Called by 'Enter' key submit on filter fields form */
    $scope.on_filter_enter_key = function(){
        if ($scope.is_project){
            $scope.do_update_project_buildings_filters();
        } else {
            $scope.do_update_buildings_filters();
        }
    };

    /* Called by 'Update Filters' click in buildings list UI */
    $scope.do_update_buildings_filters = function(){
        $scope.search.deselect_all_buildings();
        refresh_search();
    };

    /* Called by 'Update Filters' click in projects buildings list UI */
    $scope.do_update_project_buildings_filters = function(){
        $scope.search.deselect_all_buildings();
        refresh_search();
    };

    /*  private function to refresh search, called by UI event handlers
        or internal methods */
    var refresh_search = function() {
        $scope.search.filter_search();
    };

    /**
    * END SEARCH CODE
    */

    /**
    *  Code for filter dropdown
    */
    $scope.update_show_matching_filter = function(optionValue) {

        switch(optionValue){
            case SHOW_ALL:
                $scope.search.filter_params.parents__isnull = undefined;
                break;
            case SHOW_MATCHED:
                $scope.search.filter_params.parents__isnull = false;  //has parents therefore is matched
                break;
            case SHOW_UNMATCHED:
                $scope.search.filter_params.parents__isnull = true;   //does not have parents therefore is unmatched
                break;
            default:
                $log.error("#matching_controller: unexpected filter value: ", optionValue);
                return;
        }
        $scope.do_update_buildings_filters();
    };

    /**
    * LABELS CODE
    */

    /*  This method is required by the ngTagsInput input control.
    */
    $scope.loadLabelsForFilter = function(query) {
        return _.filter($scope.labels, function(lbl) {
            if(_.isEmpty(query)) {
                // Empty query so return the whole list.
                return true;
            } else {
                // Only include element if it's name contains the query string.
                return lbl.name.indexOf(query) > -1;
            }
        });
    };

    $scope.$watchCollection("selected_labels", function() {
        // Only submit the `id` of the label to the API.
        if($scope.selected_labels.length > 0) {
            $scope.search.filter_params.canonical_building__labels = _.pluck($scope.selected_labels, "id");
        } else {
            delete $scope.search.filter_params.canonical_building__labels;
        }

    });

    /**
        Opens the update building labels modal.
        All further actions for labels happen with that modal and its related controller,
        including creating a new label or applying to/removing from a building.
        When the modal is closed, refresh labels and search.
     */
    $scope.open_update_building_labels_modal = function() {

        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/update_building_labels_modal.html',
            controller: 'update_building_labels_modal_ctrl',
            resolve: {
                search: function () {
                    return $scope.search;
                }
            }
        });
        modalInstance.result.then(
            function () {
                //dialog was closed with 'Done' button.
                get_labels();
                refresh_search();
            }, 
            function (message) {
               //dialog was 'dismissed,' which means it was cancelled...so nothing to do. 
            }
        );
   
    };

    /**
    * get_labels: called by init, gets available organization labels
    */
    var get_labels = function(building) {
        // gets all labels for an org user
        label_service.get_labels().then(function(data) {
            // resolve promise
            $scope.labels = data.results;
        });
    };

    /**
    * END LABELS CODE
    */


    /**
     * BUILDING TABLE CODE
     */

    /**
     * get_columns: called by init, sets the table columns
     */
    var get_columns = function() {
        $scope.assessor_fields = all_columns.fields;
        $scope.search.init_storage($location.$$path);
        $scope.columns = $scope.search.generate_columns(
            all_columns.fields,
            default_columns.columns,
            $scope.search.column_prototype
        );
    };

    /**
    * END BUILDING TABLE CODE
    */

    var init_matching_dropdown = function() {
        $scope.matching_filter_options = [
            {id:SHOW_ALL, value:SHOW_ALL},
            {id:SHOW_MATCHED, value:SHOW_MATCHED},
            {id:SHOW_UNMATCHED, value:SHOW_UNMATCHED}
        ];

        // Initial dropdown state depends on cached filter attrs.
        switch($scope.search.filter_params.parents__isnull){
            case undefined:
                $scope.matching_filter_options_init = SHOW_ALL;
                break;
            case false:
                $scope.matching_filter_options_init = SHOW_MATCHED;
                break;
            case true:
                $scope.matching_filter_options_init = SHOW_UNMATCHED;
                break;
            default:
                $scope.matching_filter_options_init = SHOW_ALL;
                return;
        }
    };

    /**
     * PROJECTS CODE
     */

    $scope.begin_add_buildings_to_new_project = function() {
        $scope.set_initial_project_state();
    };

    $scope.begin_add_buildings_to_existing_project = function(){
        $scope.selected_existing_project = null;
        $scope.create_project_state='create';
    };


    $scope.nothing_selected = function() {
        if ($scope.search.selected_buildings.length === 0 &&
            $scope.search.select_all_checkbox === false) {
            return true;
        } else {
            return false;
        }
    };
    $scope.nothing_selected_cursor = function() {
        if ($scope.nothing_selected()) {
            return {'cursor': "not-allowed"};
        } else {
            return {};
        }
    };
    $scope.create_project = function() {
        $scope.progress_percentage = 0;
        project_service.create_project($scope.project).then(function(data) {
            // resolve promise
            // should add banner here for success and maybe redirect
            $scope.$emit('project_created');
            $scope.add_buildings(data.project_slug);
        }, function(data, status) {
            // reject promise
            // project name already exists
            console.log(data);
            $scope.create_project_error = true;
            $scope.create_project_error_message = data.message;

        });
    };
    $scope.add_buildings = function(project_slug) {
        $scope.create_project_state = 'adding';
        $scope.project.project_slug = project_slug;
        $scope.project.selected_buildings = $scope.search.selected_buildings;
        $scope.project.select_all_checkbox = $scope.search.select_all_checkbox;
        $scope.project.filter_params = $scope.search.filter_params;
        $scope.project.order_by = $scope.search.order_by;
        $scope.project.sort_reverse = $scope.search.sort_reverse;

        project_service.add_buildings($scope.project).then(function(data) {
            // resolve promise
            $scope.project.project_loading_cache_key = data.project_loading_cache_key;
            monitor_adding_buildings(data.project_loading_cache_key);
        });
    };
    var monitor_adding_buildings = function(cache_key) {
        var stop = $timeout(function(){
            project_service.add_buildings_status(cache_key).then(function(data) {
                // resolve promise
                if (typeof data.progress_object !== "undefined" && data.progress_object !== null && typeof data.progress_object.progress !== "undefined") {
                    $scope.progress_percentage = data.progress_object.progress;
                    $scope.progress_numerator = data.progress_object.numerator;
                    $scope.progress_denominator = data.progress_object.denominator;
                    if (data.progress_object.progress < 100) {
                        monitor_adding_buildings(cache_key);
                    } else {
                        $scope.create_project_state = 'success';
                        init();
                        refresh_search();
                    }
                } else {
                    monitor_adding_buildings(cache_key);
                }
            });
        }, 250);
    };
    $scope.go_to_project = function(project_slug) {
        angular.element('.modal-backdrop').hide();
        angular.element('body').removeClass('modal-open');
        angular.element('#newProjectModal').modal('hide');


        if (typeof project_slug === "undefined") {
            $location.path('/projects/' + $scope.project.project_slug);
        } else {
            $location.path('/projects/' + project_slug);
        }
    };
    $scope.number_to_remove = function() {
        if ($scope.search.select_all_checkbox) {
            return $scope.search.number_matching_search - $scope.search.selected_buildings.length;
        } else {
            return $scope.search.selected_buildings.length;
        }
    };
    $scope.remove_buildings = function() {
        $scope.create_project_state = 'removing';
        $scope.project.selected_buildings = $scope.search.selected_buildings;
        $scope.project.filter_params = $scope.search.filter_params;
        $scope.project.select_all_checkbox = $scope.search.select_all_checkbox;
        $scope.project.filter_params = $scope.search.filter_params;
        $scope.project.order_by = $scope.search.order_by;
        $scope.project.sort_reverse = $scope.search.sort_reverse;
        project_service.remove_buildings($scope.project).then(function(data){
            // resolve promise
            $scope.search.selected_buildings = [];
            $scope.search.select_all_checkbox = false;
            monitor_adding_buildings(data.project_removing_cache_key);
        });
    };
    $scope.move_buildings = function(project_slug) {
        var copy = false;
        transfer_buildings(project_slug, copy);
    };
    $scope.copy_buildings = function(project_slug) {
        var copy = true;
        transfer_buildings(project_slug, copy);
    };
    var transfer_buildings = function(project_slug, copy) {
        var search_params = {
            'q': $scope.query,
            'filter_params': $scope.search.filter_params,
            'project_slug': $scope.project.id || null
        };

        project_service.move_buildings($scope.user.project_id, project_slug, $scope.search.selected_buildings, $scope.search.select_all_checkbox, search_params, copy).then(function(data) {
            // resolve promise
            $scope.create_project_state = 'success';
            init();
        }, function(data, status) {
            // reject promise
            console.log({data: data, status: status});
        });
    };
    $scope.set_initial_project_state = function() {
        $scope.create_project_error = false;
        $scope.create_project_error_message = "";
        $scope.create_project_state = 'create';
        $scope.project.compliance_type = null;
        $scope.project.name = null;
        $scope.project.deadline_date = null;
        $scope.project.end_date = null;
    };

    /**
     * open_export_modal: opens the export modal
     */
    $scope.open_export_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/export_modal.html',
            controller: 'export_modal_controller',
            resolve: {
                search: function () {
                    return $scope.search;
                },
                selected_fields: function () {
                    return $scope.columns.map(function (col) {
                        return col.sort_column;
                    });
                },
                project: function () {
                    return $scope.project;
                }
            }
        });

        modalInstance.result.then(
            function () {
        }, function (message) {
                $log.info(message);
                $log.info('Modal dismissed at: ' + new Date());
        });
    };

    /**
     * open_delete_modal: opens the delete buildings modal
     */
    $scope.open_delete_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/delete_modal.html',
            controller: 'delete_modal_controller',
            resolve: {
                search: function () {
                    return $scope.search;
                }
            }
        });

        modalInstance.result.then(
            function () {
                $scope.search.selected_buildings = [];
                refresh_search();
        }, function (message) {
                refresh_search();
        });
    };
    /**
    * END PROJECTS CODE
    */


    /**
     * broadcasts
     */
    $scope.$on('projects_updated', function() {
        // get new list of projects
        init();
    });
    /**
     * end broadcasts
     */


    /**
     * open_edit_columns_modal: modal to set which columns a user has in the
     *   table
     */
    $scope.open_edit_columns_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/custom_view_modal.html',
            controller: 'buildings_settings_controller',
            resolve: {
                'all_columns': function() {
                    return all_columns;
                },
                'default_columns': function() {
                    return default_columns;
                },
                'buildings_payload': function() {
                    return {};
                },
                'shared_fields_payload': function() {
                    return {show_shared_buildings: false};
                },
                'project_payload': function() {
                    return {project: {}};
                },
                'building_payload': function() {
                    return {'building': {}};
                }
            }
        });
        modalInstance.result.then(
            function (columns) {
                // update columns
                $scope.columns = $scope.search.generate_columns(
                    all_columns.fields,
                    columns,
                    $scope.search.column_prototype
                );
                refresh_search();
        }, function (message) {
        });
    };


    /**
     * init: fired on controller load
     *  - grabs the search and filter parameters from the window location and
     *    sets them
     *  - checks to see if the controller is service
     *    the main buildings list or a project buildings list. If a project it
     *    fetches some project info and updates the DOM.
     *  - updates the pagination
     *  - gets all projects so a user can copy or move buildings between
     *    projects
     *  - sets the table columns
     *  - gets labels for use in a project
     */
    var init = function() {
        // get search params from window location and populate the input filters
        $scope.search.filter_params = $location.search();
        $scope.search.query = $scope.search.filter_params.q || "";
        $scope.search.update_results(search_payload);

        // intitialize tooltips
        $('[data-toggle="popover"]').popover();

        if (typeof $scope.user.project_id !== "undefined") {
            $scope.is_project = true;
            $scope.search.filter_params.project__slug = $scope.user.project_id;
            project_service.get_project($scope.user.project_id).then(function(data) {
                // resolve promise
                $scope.project = data.project;
            }, function(data, status) {
                // reject promise
                console.log({data: data, status: status});
            });
        } else {
            $scope.is_project = false;
        }

        project_service.get_projects().then(function(data) {
             // resolve promise
            $scope.projects = data.projects;
            if (typeof $scope.user.project_id !== "undefined") {
                for (var i = 0; i < $scope.projects.length; i++) {
                    if ($scope.projects[i].slug === $scope.user.project_id) {
                        $scope.projects.splice(i, 1);
                        break;
                    }
                }
            }
        });

        get_columns();
        get_labels();
        init_matching_dropdown();

    };
    init();
}]);
