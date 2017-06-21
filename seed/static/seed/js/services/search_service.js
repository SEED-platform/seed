/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
    'spinner_utility',
    function ($http,
              spinner_utility) {
      /************
       * variables
       */
      var search_service = {
        url: '',
        buildings: [],
        alert: false,
        error_message: '',
        number_matching_search: 0,
        selected_buildings: [],
        columns: [],
        labels: [],
        sort_column: 'tax_lot_id',
        select_all_checkbox: false,
        current_page: 1,
        number_per_page: 10,
        order_by: '',
        sort_reverse: false,
        is_loading: false,
        query: '',
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
        start: 1,
        end: (search_service.number_matching_search > 10) ? 10 :
          search_service.number_matching_search
      };
      var saas; // set to the local instance of the extended search_service this

      /************
       * functions
       */

      // unused 6.15.17 commented out for code cov dbressan
      // search_service.init_storage = function (prefix) {
      //   // Check session storage for order and sort values.
      //   if (!_.isUndefined(Storage)) {
      //     saas.prefix = prefix;
      //
      //     // order_by & sort_column
      //     if (sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy') !== null) {
      //       saas.order_by = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
      //       saas.sort_column = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
      //     }
      //
      //     // sort_reverse
      //     if (sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse') !== null) {
      //       saas.sort_reverse = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse'));
      //     }
      //
      //     // filter_params
      //     if (sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams') !== null) {
      //       saas.filter_params = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams'));
      //     }
      //
      //     // number_per_page
      //     if (sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage') !== null) {
      //       saas.number_per_page = saas.number_per_page_options_model = saas.showing.end =
      //         JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingNumberPerPage'));
      //     }
      //
      //     // current_page
      //     if (sessionStorage.getItem(prefix + ':' + 'seedBuildingPageNumber') !== null) {
      //       saas.current_page = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingPageNumber'));
      //       saas.update_start_end_paging();
      //       saas.update_buttons();
      //     }
      //   }
      // };

      // unused 6.15.17 commented out for code cov dbressan
      // search_service.clear_filters = function () {
      //   saas.filter_params = {};
      //   if (!_.isUndefined(Storage)) {
      //     sessionStorage.setItem(this.prefix + ':' + 'seedBuildingFilterParams', {});
      //   }
      //   saas.filter_search();
      // };

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
       * construct_search_query: constructs an object suitable to be passed to
       * the api to search for a set of buildings.
       */
      search_service.construct_search_query = function (query) {
        this.sanitize_params();
        return {
          q: query || this.query,
          number_per_page: this.number_per_page,
          page: this.current_page,
          order_by: this.order_by,
          sort_reverse: this.sort_reverse,
          filter_params: this.filter_params
        };
      };

      /**
       * search_buildings: makes a search request. ``url`` must be set before
       * a request can be made successfully.
       *
       * @param {string} query (optional) cross field search, if undefined,
       *   search_buildings will use search_service.query
       */
      search_service.search_buildings = function (query) {
        this.sanitize_params();
        this.query = query || this.query;
        var that = this;
        var data = _.defaults({number_per_page: 999999999}, this.construct_search_query(query));
        spinner_utility.show();
        return $http.post(that.url, data).then(function (response) {
          spinner_utility.hide();
          that.update_results(response.data);
          return response.data;
        }).catch(function () {
          that.error_message = 'error: ' + status + ' ' + data;
          that.alert = true;
        });
      };


      /**
       * update_results: updates the pagination and table after success. Can be
       *   used with a search payload to update or populate a table.
       */
      search_service.update_results = function (data) {
        // safely handle no data back
        saas = this;

        data = data || {};
        this.buildings = data.buildings || [];
        this.number_matching_search = data.number_matching_search || 0;
        this.alert = false;
        this.error_message = '';
        // Num Pages is now a method to allow for it to be up to date.
        // console.log("Number per page: " + this.number_per_page);
        // console.log("Number of pages: " + this.num_pages());

        this.update_start_end_paging();
        this.update_buttons();
        this.select_or_deselect_all_buildings();
        this.load_state_from_selected_buildings();
      };


      /**
       * filter_search: triggered when a filter param changes
       */
      search_service.filter_search = function () {
        this.current_page = 1;
        this.search_buildings();
        if (!_.isUndefined(Storage)) {
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
      search_service.update_number_per_page = function () {
        // this refers to the pagination object not search_service
        this.number_per_page = this.number_per_page_options_model;
        this.current_page = 1;
        this.search_buildings();
        if (!_.isUndefined(Storage)) {
          sessionStorage.setItem(this.prefix + ':' + 'seedBuildingNumberPerPage', JSON.stringify(this.number_per_page));
        }
      };

      /**
       * update_start_end_paging: controls the display of `showing 31 to 40 of
       *   1,000 buildings` and is called after a successful search
       */
      search_service.update_start_end_paging = function () {
        if (this.current_page === this.num_pages()) {
          this.showing.end = this.number_matching_search;
        } else {
          this.showing.end = this.current_page * this.number_per_page;
        }

        this.showing.start = ((this.current_page - 1) * this.number_per_page) + 1;
      };

      // unused 6.15.17 commented out for code cov dbressan
      /**
       * first_page: triggered when the `first` paging button is clicked, it
       *   sets the page to the first in the results, and fetches that page
       */
      // search_service.first_page = function () {
      //   this.current_page = 1;
      //   if (!_.isUndefined(Storage)) {
      //     sessionStorage.setItem(this.prefix + ':' + 'seedBuildingPageNumber', this.current_page);
      //   }
      //   this.search_buildings();
      // };

      /**
       * num_pages: return the number of pages that are expected based on the
       * total matches and the number_per_page setting
       */
      search_service.num_pages = function () {
        return Math.ceil(
          this.number_matching_search / this.number_per_page
        );
      };

      // unused 6.15.17 commented out for code cov dbressan
      /**
       * last_page: triggered when the `last` paging button is clicked, it
       *   sets the page to the last in the results, and fetches that page
       */
      // search_service.last_page = function () {
      //   if (!_.isUndefined(Storage)) {
      //     sessionStorage.setItem(this.prefix + ':' + 'seedBuildingPageNumber', this.current_page);
      //   }
      //   this.current_page = this.num_pages();
      //   if (!_.isUndefined(Storage)) {
      //     sessionStorage.setItem(this.prefix + ':' + 'seedBuildingPageNumber', this.current_page);
      //   }
      //   this.search_buildings();
      // };

      /**
       * next_page: triggered when the `next` paging button is clicked, it
       *   increments the page of the results, and fetches that page
       */
      search_service.next_page = function () {
        this.current_page += 1;
        if (this.current_page > this.num_pages()) {
          this.current_page = this.num_pages();
        }
        if (!_.isUndefined(Storage)) {
          sessionStorage.setItem(this.prefix + ':' + 'seedBuildingPageNumber', this.current_page);
        }
        this.search_buildings();
      };

      /**
       * prev_page: triggered when the `previous` paging button is clicked, it
       *   decrements the page of the results, and fetches that page
       */
      search_service.prev_page = function () {
        this.current_page -= 1;
        if (this.current_page < 1) {
          this.current_page = 1;
        }
        if (!_.isUndefined(Storage)) {
          sessionStorage.setItem(this.prefix + ':' + 'seedBuildingPageNumber', this.current_page);
        }
        this.search_buildings();
      };

      /**
       * update_buttons: sets the previous and next buttons' disabled state
       */
      search_service.update_buttons = function () {
        // body goes here
        this.prev_page_disabled = this.current_page === 1;
        this.next_page_disabled = this.current_page === this.num_pages();
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
      search_service.add_remove_to_list = function (building) {
        if (((building.checked && !this.select_all_checkbox) ||
          (!building.checked && this.select_all_checkbox)) && !_.includes(this.selected_buildings, building.id)) {
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
      search_service.select_or_deselect_all_buildings = function () {
        for (var i = 0; i < this.buildings.length; i++) {
          this.buildings[i].checked = this.select_all_checkbox;
        }
      };

      /**
       * select_all_changed: fired when the select all checkbox is
       *   checked
       */
      search_service.select_all_changed = function () {
        this.selected_buildings = [];
        this.select_or_deselect_all_buildings();
      };

      /**
       * load_state_from_selected_buildings: recall a building's checked state
       *   between server side pagination loads. This should **always** be called
       *   after select_or_deselect_all_buildings.
       */
      search_service.load_state_from_selected_buildings = function () {
        for (var i = 0; i < this.buildings.length; i++) {
          if (_.includes(this.selected_buildings, this.buildings[i].id)) {
            this.buildings[i].checked = !this.select_all_checkbox;
          }
        }
      };
      /**
       * end checkbox logic
       */

      // unused 6.15.17 commented out for code cov dbressan
      /** deselect_all_buildings: Force a deselection of all buildings
       *
       */
      // search_service.deselect_all_buildings = function () {
      //   var len = this.buildings.length;
      //   for (var bldg_index = 0; bldg_index < len; bldg_index++) {
      //     this.buildings[bldg_index].checked = false;
      //   }
      //   this.selected_buildings = [];
      //   this.select_all_checkbox = false;
      // };


      /**
       * table columns logic
       */

      /**
       * column_prototype: extended object used for column headers, it adds
       *   the sort and filter methods, and various classes
       */
      search_service.column_prototype = {
        // unused 6.15.17 commented out for code cov dbressan
        // toggle_sort: function () {
        //   if (this.sortable) {
        //     if (saas.sort_column === this.sort_column) {
        //       saas.sort_reverse = !saas.sort_reverse;
        //     } else {
        //       saas.sort_reverse = true;
        //       saas.sort_column = this.sort_column;
        //     }
        //   }
        //
        //   if (!_.isUndefined(Storage)) {
        //     sessionStorage.setItem(this.prefix + ':' + 'seedBuildingOrderBy', saas.sort_column);
        //     sessionStorage.setItem(this.prefix + ':' + 'seedBuildingSortReverse', saas.sort_reverse);
        //   }
        //
        //   saas.order_by = this.sort_column;
        //   saas.current_page = 1;
        //   saas.search_buildings();
        // },
        is_sorted_on_this_column: function () {
          return this.sort_column === saas.sort_column;
        },
        // unused 6.15.17 commented out for code cov dbressan
        // is_sorted_down: function () {
        //   return this.is_sorted_on_this_column() && saas.sort_reverse;
        // },
        // is_sorted_up: function () {
        //   return this.is_sorted_on_this_column() && !saas.sort_reverse;
        // },
        is_unsorted: function () {
          return !this.is_sorted_on_this_column();
        }
        // unused 6.15.17 commented out for code cov dbressan
        // sorted_class: function () {
        //   if (saas.sort_column === this.sort_column) {
        //     if (saas.sort_reverse) {
        //       return 'sorted sort_asc';
        //     } else {
        //       return 'sorted sort_desc';
        //     }
        //   } else {
        //     return '';
        //   }
        // },
        // is_label: function () {
        //   return this.sort_column === 'project_building_snapshots__status_label__name';
        // }
      };

      /**
       * generate_columns: creates a list of column objects extended from column
       *   prototype by filtering the list of all possible columns
       */
      search_service.generate_columns = function (all_columns, column_headers, column_prototype) {
        var columns = all_columns.filter(function (c) {
          return _.includes(column_headers, c.sort_column) || c.checked;
        });
        // also apply the user sort order
        columns.sort(function (a, b) {
          // when viewing the list of projects, there is an extra "Status" column that is always first
          if (a.sort_column === 'project_building_snapshots__status_label__name') {
            return -1;
          } else if (b.sort_column === 'project_building_snapshots__status_label__name') {
            return 1;
          }
          // if no status, sort according to user's selected order
          if (_.includes(column_headers, a.sort_column) && _.includes(column_headers, b.sort_column)) {
            return (column_headers.indexOf(a.sort_column) - column_headers.indexOf(b.sort_column));
          } else if (_.includes(column_headers, a.sort_column)) {
            return -1;
          } else if (_.includes(column_headers, b.sort_column)) {
            return 1;
          } else { // preserve previous order
            return (all_columns.indexOf(a) - all_columns.indexOf(b));
          }
        });

        if (!_.isUndefined(column_prototype)) {
          for (var i = 0; i < columns.length; i++) {
            angular.extend(columns[i], column_prototype);
          }
        }
        return columns;
      };

      return search_service;
    }]);
