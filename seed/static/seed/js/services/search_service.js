/**
 * :copyright: (c) 2014 Building Energy Inc
 */
/**
 *
 * Search as a Service (saas)
 *
 * initial work: http://plnkr.co/edit/Vm5MR9KYYXl3pkIKyWsd?p=preview
 *
 * search_service: include the module 'config.seed.service.search' in your app
 *                 to have access to ``search_service``. ``search_service``
 *                 should be extended by a controller's scope to gain access
 *                 to a smattering of common variables and functions needed to
 *                 use a server-side search. Assuming a table within a
 *                 controller's scope follows the same conventions, extending
 *                 search across an app should be less painful.
 *
 *                 This is by design with side-effects.
 *
 * Usage: In the scope, include 'search_service' as one of the controller's
 *        dependencies, then extend the scope with the service.
 *
 *        `$scope.search = angular.copy(search_service);`
 *
 *        Now the scope will have access to all the search_service properties.
 *
 *        To make a search request, set the `url` to the AJAX endpoint and
 *        fire off a search.
 *
 * Ex: $scope.url = "/app/search";
 *     $scope.search_buildings("holiday inn").then(function(data){
 *       // do something with the search result
 *       // $scope.buildings will be auto-updates as will the pagination
 *     });
 */
angular.module('BE.seed.service.search', [])
.factory('search_service', [
  '$http',
  '$q',
  function ($http, $q) {
    /************
     * variables
     */
    var search_service = {
        url: "",
        buildings: [],
        alert: false,
        error_message: "",
        number_matching_search: 0,
        selected_buildings: [],
        columns: [],
        labels: [],
        sort_column: "tax_lot_id",
        select_all_checkbox: false,
        current_page: 1,
        number_per_page: 10,
        order_by: "",
        sort_reverse: false,
        is_loading: false,
        num_pages: 0,
        query: "",
        number_per_page_options: [10, 25, 50, 100],
        number_per_page_options_model: 10,
        filter_params: {},
        prev_page_disabled: true,
        has_checkbox: true,
        prefix: ''
    };
    search_service.next_page_disabled = (
        search_service.number_matching_search <= 10);
    search_service.showing = {
        'start': 1,
        'end': (search_service.number_matching_search > 10) ? 10 :
            search_service.number_matching_search
    };
    var saas; // set to the local instance of the extended search_service this

    /************
     * functions
     */

    search_service.init_storage = function (prefix) {
        // Check session storage for order and sort values.
        if (typeof(Storage) !== "undefined") {
            saas.prefix = prefix;

            // order_by & sort_column
            if (sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy') !== null){
                saas.order_by = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
                saas.sort_column = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
            }

            // sort_reverse
            if (sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse') !== null) {
                saas.sort_reverse = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse'));
            }

            // filter_params
            if (sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams') !== null) {
                saas.filter_params = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams'));
            }

            // number_per_page
            if (sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage') !== null) {
                saas.number_per_page = saas.number_per_page_options_model = saas.showing.end =
                JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage'));
            }
        }
    };

    /**
     * sanitize_params: removes filter params with null or undefined values
     */
    search_service.sanitize_params = function () {
      var params = this.filter_params;
      var to_remove = [];
      for (var prop in params) {
        if (params.hasOwnProperty(prop) &&
            ((params[prop] === undefined) ||
             (params[prop] === null) ||
             (params[prop] === ''))) {
          to_remove.push(prop);
        }
      }

      for (var i = 0; i < to_remove.length; ++i) {
        var prop_to_delete = to_remove[i];
        delete params[prop_to_delete];
      }
    };

    /**
     * search_buildings: makes a search request. ``url`` must be set before
     * a request can be made successfully.
     *
     * @param {string} query (optional) cross field search, if undefined,
     *   search_buildings will use search_service.query
     */
    search_service.search_buildings = function(query) {
        this.sanitize_params();
        var defer = $q.defer();
        var that = this;
        that.query = query || that.query;
        $http({
            'method': 'POST',
            'data': {
                'q': that.query,
                'number_per_page': that.number_per_page,
                'page': that.current_page,
                'order_by': that.order_by,
                'sort_reverse': that.sort_reverse,
                'filter_params': that.filter_params
            },
            'url': that.url
        }).success(function(data, status, headers, config){
            that.update_results(data);
            defer.resolve(data);
        }).error(function(data, status, headers, config){
            that.error_message = "error: " + status + " " + data;
            that.alert = true;
            defer.reject(data, status);
        });
        return defer.promise;
    };


    /**
     * update_results: updates the pagination and table after success. Can be
     *   used with a search payload to update or populate a table.
     */
    search_service.update_results = function(data) {
        // safely handle no data back
        saas = this;
        data = data || {};
        this.buildings = data.buildings || [];
        this.number_matching_search = data.number_matching_search || 0;
        this.alert = false;
        this.error_message = "";
        this.num_pages = Math.ceil(
            this.number_matching_search / this.number_per_page
        );
        this.update_start_end_paging();
        this.update_buttons();
        this.select_or_deselect_all_buildings();
        this.load_state_from_selected_buildings();
    };


    /**
     * filter_search: triggered when a filter param changes
     */
    search_service.filter_search = function() {
        this.current_page = 1;
        this.search_buildings();
        if (typeof(Storage) !== "undefined") {
            sessionStorage.setItem(this.prefix + ':' + 'seedBuildingFilterParams', JSON.stringify(this.filter_params));
        }
    };


    /**
     * Pagination code
     */

    /**
     * update_number_per_page: fired when a user picks an option in the number
     *   per page select, `update_number_per_page` updates the pagination model
     *   and queries the search again to get more data
     */
    search_service.update_number_per_page = function() {
        // this refers to the pagination object not search_service
        this.number_per_page = this.number_per_page_options_model;
        this.current_page = 1;
        this.search_buildings();
        if (typeof(Storage) !== "undefined") {
            sessionStorage.setItem(this.prefix + ':' + 'seedBuildingNumberPerPage', JSON.stringify(this.number_per_page));
        }
    };

    /**
     * update_start_end_paging: controls the display of `showing 31 to 40 of
     *   1,000 buildings` and is called after a successful search
     */
    search_service.update_start_end_paging = function() {
        if (this.current_page === this.num_pages) {
            this.showing.end = this.number_matching_search;
        } else {
            this.showing.end = this.current_page * this.number_per_page;
        }

        this.showing.start = ((this.current_page - 1)*this.number_per_page) + 1;
    };

    /**
    * first_page: triggered when the `first` paging button is clicked, it
    *   sets the page to the first in the results, and fetches that page
    */
    search_service.first_page = function() {
      this.current_page = 1;
      this.search_buildings();
    };

    /**
    * last_page: triggered when the `last` paging button is clicked, it
    *   sets the page to the last in the results, and fetches that page
    */
    search_service.last_page = function() {
      this.current_page = this.num_pages;
      this.search_buildings();
    };

    /**
     * next_page: triggered when the `next` paging button is clicked, it
     *   increments the page of the results, and fetches that page
     */
    search_service.next_page = function() {
        this.current_page += 1;
        if (this.current_page > this.num_pages) {
            this.current_page = this.num_pages;
        }
        this.search_buildings();
    };

    /**
     * prev_page: triggered when the `previous` paging button is clicked, it
     *   decrements the page of the results, and fetches that page
     */
    search_service.prev_page = function() {
        this.current_page -= 1;
        if (this.current_page < 1) {
            this.current_page = 1;
        }
        this.search_buildings();
    };

    /**
     * update_buttons: sets the previous and next buttons' disabled state
     */
    search_service.update_buttons = function() {
        // body goes here
        this.prev_page_disabled = this.current_page === 1;
        this.next_page_disabled = this.current_page === this.num_pages;
    };
    /**
     * end pagination code
     */


    /**
     * checkbox logic (select all) and checking a building
     */

    /**
     * add_remove_to_list: adds or removes selected buildings to the array
     *   `selected_buildings`, which is also used to track which buildings are
     *   unselected if the select all checkbox is checked.
     *
     */
    search_service.add_remove_to_list = function(building) {
        if (((building.checked && !this.select_all_checkbox) ||
            (!building.checked && this.select_all_checkbox)) &&
            this.selected_buildings.indexOf(building.id) === -1) {
            this.selected_buildings.push(building.id);
        } else {
            // remove from list
            this.selected_buildings.splice(this.selected_buildings.indexOf(building.id), 1);
        }
    };

    /**
     * select_or_deselect_all_buildings: fired when the select all checkbox is
     *   checked via `select_all_changed` or after a successful search. This
     *   should **always** be called before load_state_from_selected_buildings.
     */
    search_service.select_or_deselect_all_buildings = function() {
        for (var i = 0; i < this.buildings.length; i++) {
            this.buildings[i].checked = this.select_all_checkbox;
        }
    };

    /**
     * select_all_changed: fired when the select all checkbox is
     *   checked
     */
    search_service.select_all_changed = function(){
        this.selected_buildings = [];
        this.select_or_deselect_all_buildings();
    };

    /**
     * load_state_from_selected_buildings: recall a building's checked state
     *   between server side pagination loads. This should **always** be called
     *   after select_or_deselect_all_buildings.
     */
    search_service.load_state_from_selected_buildings = function() {
        for (var i = 0; i < this.buildings.length; i++) {
            if (this.selected_buildings.indexOf(this.buildings[i].id) > -1) {
                this.buildings[i].checked = !this.select_all_checkbox;
            }
        }
    };
    /**
     * end checkbox logic
     */

    /**
     * table columns logic
     */

    /**
     * column_prototype: extended object used for column headers, it adds
     *   the sort and filter methods, and various classes
     */
    search_service.column_prototype = {
        toggle_sort: function() {
            if (this.sortable) {
                if (saas.sort_column === this.sort_column) {
                    saas.sort_reverse = !saas.sort_reverse;
                } else {
                    saas.sort_reverse = true;
                    saas.sort_column = this.sort_column;
                }
            }

            if (typeof(Storage) !== "undefined") {
                sessionStorage.setItem(saas.prefix + ':' + 'seedBuildingOrderBy', saas.sort_column);
                sessionStorage.setItem(saas.prefix + ':' + 'seedBuildingSortReverse', saas.sort_reverse);
            }

            saas.order_by = this.sort_column;
            saas.current_page = 1;
            saas.search_buildings();
        },
        is_sorted_on_this_column: function() {
            return this.sort_column === saas.sort_column;
        },
        is_sorted_down: function() {
            return this.is_sorted_on_this_column() && saas.sort_reverse;
        },
        is_sorted_up: function() {
            return this.is_sorted_on_this_column() && !saas.sort_reverse;
        },
        is_unsorted: function() {
            return !this.is_sorted_on_this_column();
        },
        sorted_class: function() {
            if (saas.sort_column === this.sort_column) {
                if (saas.sort_reverse) {
                    return "sorted sort_asc";
                } else {
                    return "sorted sort_desc";
                }
            } else {
                return "";
            }
        },
        is_label: function() {
            return this.sort_column === "project_building_snapshots__status_label__name";
        }
    };

    /**
     * generate_columns: creates a list of column objects extended from column
     *   prototype by filtering the list of all possible columns
     */
    search_service.generate_columns = function(
      all_columns,
      column_headers,
      column_prototype) {
        var columns = [];
        columns = all_columns.filter(function(c) {
            return column_headers.indexOf(c.sort_column) > -1 || c.checked;
        });
        // also apply the user sort order
        columns.sort(function(a,b) {
            // when viewing the list of projects, there is an extra "Status" column that is always first
            if (a.sort_column == 'project_building_snapshots__status_label__name') {
                return -1;
            } else if (b.sort_column == 'project_building_snapshots__status_label__name') {
                return 1;
            }
            // if no status, sort according to user's selected order
            if (column_headers.indexOf(a.sort_column) > -1 && column_headers.indexOf(b.sort_column) > -1) {
                return (column_headers.indexOf(a.sort_column) - column_headers.indexOf(b.sort_column));
            } else if (column_headers.indexOf(a.sort_column) > -1) {
                return -1;
            } else if (column_headers.indexOf(b.sort_column) > -1) {
                return 1;
            } else { // preserve previous order
                return (all_columns.indexOf(a) - all_columns.indexOf(b));
            }
        });

        for (var i = 0; i < columns.length; i++) {
            angular.extend(columns[i], column_prototype);
        }
        return columns;
    };

    return search_service;
}]);
