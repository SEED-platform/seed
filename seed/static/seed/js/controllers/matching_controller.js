/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching', [])
  .controller('matching_controller', [
    '$scope',
    '$state',
    '$stateParams',
    'import_file_payload',
    'inventory_payload',
    'building_services',
    'default_columns',
    'all_columns',
    'cycles',
    'urls',
    '$uibModal',
    '$log',
    'search_service',
    'matching_service',
    'inventory_service',
    '$filter',
    function ($scope,
              $state,
              $stateParams,
              import_file_payload,
              inventory_payload,
              building_services,
              default_columns,
              all_columns,
              cycles,
              urls,
              $uibModal,
              $log,
              search_service,
              matching_service,
              inventory_service,
              $filter) {
      // Remove import_files that haven't yet been mapped
      _.remove(import_file_payload.import_file.dataset.importfiles, function (importfile) {
        return importfile.mapping_done !== true;
      });

      $scope.search = angular.copy(search_service);
      $scope.search.url = urls.search_buildings;

      $scope.import_files = import_file_payload.import_file;
      var validCycles = _.uniq(_.map(import_file_payload.import_file.dataset.importfiles, 'cycle'));
      $scope.cycles = _.filter(cycles.cycles, function (cycle) {
        return _.includes(validCycles, cycle.id);
      });
      $scope.selectedCycle = _.find($scope.cycles, {id: $scope.import_files.cycle});
      if ($scope.inventory_type == 'properties') {
        $scope.inventory = inventory_payload.properties;
      } else {
        $scope.inventory = inventory_payload.tax_lots;
      }
      $scope.q = '';
      $scope.number_per_page = 10;
      $scope.current_page = 1;
      $scope.order_by = '';
      $scope.sort_reverse = false;
      $scope.filter_params = {};
      $scope.existing_filter_params = {};
      $scope.project_slug = null;
      $scope.number_properties_matching_search = 0;
      $scope.number_tax_lots_matching_search = 0;
      $scope.number_properties_returned = 0;
      $scope.number_tax_lots_returned = 0;
      $scope.pagination = {};
      $scope.prev_page_disabled = false;
      $scope.next_page_disabled = false;
      $scope.showing = {};
      $scope.pagination.number_per_page_options = [10, 25, 50, 100];
      $scope.pagination.number_per_page_options_model = 10;
      $scope.loading_pills = true;
      $scope.show_building_list = true;
      $scope.selected_row = '';
      $scope.fields = all_columns.fields;
      $scope.default_columns = default_columns.columns;
      $scope.columns = [];
      $scope.alerts = [];
      $scope.file_select = {
        file: $scope.import_files.dataset.importfiles[0]
      };
      $scope.detail = {
        match_tree: []
      };
      $scope.importfile_id = $stateParams.importfile_id;
      $scope.inventory_type = $stateParams.inventory_type;
      var order_by = $filter('orderBy');

      /* Handle 'update filters' button click */
      $scope.do_update_filters = function () {
        $scope.current_page = 1;
        $scope.filter_search();
      };

      /* Handle 'Enter' key on filter fields */
      $scope.on_filter_enter_key = function () {
        $scope.current_page = 1;
        $scope.filter_search();
      };

      /*
       * filter_search: searches TODO(ALECK): use the search_service for search
       *   and pagination here.
       */
      $scope.filter_search = function () {
        $scope.update_number_matched();
        inventory_service.search_matching_inventory($scope.q, $scope.number_per_page, $scope.current_page,
          $scope.order_by, $scope.sort_reverse, $scope.filter_params, $scope.file_select.file.id)
          .then(function (data) {
            // safe-guard against future init() calls
            inventory_payload = data;

            if ($scope.inventory_type == 'properties') {
              $scope.inventory = data.properties;
            } else {
              $scope.inventory = data.tax_lots;
            }
            $scope.number_properties_matching_search = data.number_properties_matching_search;
            $scope.number_tax_lots_matching_search = data.number_tax_lots_matching_search;
            $scope.number_properties_returned = data.number_properties_returned;
            $scope.number_tax_lots_returned = data.number_tax_lots_returned;
            if ($scope.inventory_type == 'properties') {
              $scope.num_pages = Math.ceil(data.number_properties_matching_search / $scope.number_per_page);
            } else {
              $scope.num_pages = Math.ceil(data.number_tax_lots_matching_search / $scope.number_per_page);
            }
            update_start_end_paging();
          })
          .catch(function (data, status) {
            console.log({data: data, status: status});
            $scope.alerts.push({type: 'danger', msg: 'Error searching'});
          });
      };


      $scope.closeAlert = function (index) {
        $scope.alerts.splice(index, 1);
      };

      /**
       *  Code for filter dropdown
       */

      var SHOW_ALL = 'Show All';
      var SHOW_MATCHED = 'Show Matched';
      var SHOW_UNMATCHED = 'Show Unmatched';

      $scope.filter_options = [
        {id: SHOW_ALL, value: SHOW_ALL},
        {id: SHOW_MATCHED, value: SHOW_MATCHED},
        {id: SHOW_UNMATCHED, value: SHOW_UNMATCHED}
      ];

      $scope.filter_selection = {selected: SHOW_ALL};     //default setting

      $scope.update_show_filter = function (optionValue) {

        switch (optionValue) {
          case SHOW_ALL:
            $scope.filter_params.children__isnull = undefined;
            break;
          case SHOW_MATCHED:
            $scope.filter_params.children__isnull = false;  //has children therefore is matched
            break;
          case SHOW_UNMATCHED:
            $scope.filter_params.children__isnull = true;   //does not have children therefore is unmatched
            break;
          default:
            $log.error('#matching_controller: unexpected filter value: ', optionValue);
            return;
        }

        $scope.current_page = 1;
        $scope.filter_search();

      };


      /**
       * Pagination code
       */
      $scope.pagination.update_number_per_page = function () {
        $scope.number_per_page = $scope.pagination.number_per_page_options_model;
        $scope.filter_search();
      };
      var update_start_end_paging = function () {
        if ($scope.current_page === $scope.num_pages) {
          if ($scope.inventory_type == 'properties') {
            $scope.showing.end = $scope.number_properties_matching_search;
          } else {
            $scope.showing.end = $scope.number_tax_lots_matching_search;
          }
        } else {
          $scope.showing.end = $scope.current_page * $scope.number_per_page;
        }

        $scope.showing.start = ($scope.current_page - 1) * $scope.number_per_page + 1;
        $scope.prev_page_disabled = $scope.current_page === 1;
        $scope.next_page_disabled = $scope.current_page === $scope.num_pages;

      };

      /**
       * first_page: triggered when the `first` paging button is clicked, it
       *   sets the results to the first page and shows that page
       */
      $scope.pagination.first_page = function () {
        $scope.current_page = 1;
        $scope.filter_search();
      };

      /**
       * last_page: triggered when the `last` paging button is clicked, it
       *   sets the results to the last page and shows that page
       */
      $scope.pagination.last_page = function () {
        $scope.current_page = $scope.num_pages;
        $scope.filter_search();
      };

      /**
       * next_page: triggered when the `next` paging button is clicked, it
       *   increments the page of the results, and fetches that page
       */
      $scope.pagination.next_page = function () {
        $scope.current_page += 1;
        if ($scope.current_page > $scope.num_pages) {
          $scope.current_page = $scope.num_pages;
        }
        $scope.filter_search();
      };

      /**
       * prev_page: triggered when the `previous` paging button is clicked, it
       *   decrements the page of the results, and fetches that page
       */
      $scope.pagination.prev_page = function () {
        $scope.current_page -= 1;
        if ($scope.current_page < 1) {
          $scope.current_page = 1;
        }
        $scope.filter_search();
      };
      /**
       * end pagination code
       */

      /**
       * toggle_match: creates or removes a match between a building and
       *   co_parent or suggested co_parent.
       *
       * @param {obj} building: building object to match or unmatch
       */
      $scope.toggle_match = function (building) {
        var source, target, create;
        if (building.coparent && building.coparent.id) {
          if (building.matched) {
            source = building.id;
            target = building.coparent.id;
          } else {
            source = building.coparent.id;
            target = building.id;
          }
          create = building.matched;
        } else {
          building.matched = false;
          return;
        }

        // creates or removes a match
        var save_promise = null;
        if ($scope.inventory_type == 'properties') save_promise = inventory_service.save_property_match(source, target, create);
        else save_promise = inventory_service.save_taxlot_match(source, target, create);
        save_promise.then(function (data) {
          // update building and coparent's child in case of a unmatch
          // without a page refresh
          if (building.matched) {
            building.children = building.children || [0];
            building.children[0] = data.child_id;
          }
          $scope.update_number_matched();
          $scope.$emit('finished_saving');
        }, function (data, status) {
          building.matched = !building.matched;
          $scope.$emit('finished_saving');
        });
      };

      /*
       * match_building: loads/shows the matching detail table and hides the
       *  matching list table
       */
      $scope.match_building = function (building) {
        // shows a matched building detail page
        $scope.search.filter_params = {};
        // chain promises to exclude the match_tree from the search of
        // existing buildings
        matching_service.get_match_tree(building.id)
          .then(function (data) {
            $scope.tip = data.tip;
            $scope.detail.match_tree = data.coparents.map(function (b) {
              // the backend doesn't set a matched field so add one here
              b.matched = true;
              return b;
            }).filter(function (b) {
              // this is tricky, we only want to show the tree nodes which
              // are original, i.e. don't have parents
              if (b.id !== building.id) {
                return b;
              }
            });
            $scope.search.filter_params.exclude = {
              id__in: data.coparents.map(function (b) {
                return b.id;
              }).concat([building.id])
            };
            return $scope.search.search_buildings();
          })
          .then(function (data) {
            $scope.$broadcast('matching_loaded', {
              matching_buildings: data.buildings,
              building: building
            });
            console.log({building: building, match_tree: $scope.detail.match_tree});
            $scope.show_building_list = false;
            $scope.selected_row = building.id;
          });

      };

      /**
       * open_edit_columns_modal: opens the edit columns modal to select and set
       *   the columns used in the matching list table and matching detail table
       */
      $scope.open_edit_columns_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/custom_view_modal.html',
          controller: 'buildings_settings_controller',
          resolve: {
            all_columns: function () {
              return all_columns;
            },
            default_columns: function () {
              return default_columns;
            },
            shared_fields_payload: function () {
              return {show_shared_buildings: false};
            },
            project_payload: function () {
              return {project: {}};
            },
            building_payload: function () {
              return {building: {}};
            }
          }
        });
      };


      /**
       * update_number_matched: updates the number of matched and unmatched
       *   buildings
       */
      $scope.update_number_matched = function () {
        building_services.get_matching_results($scope.file_select.file.id)
          .then(function (data) {
            // console.log('type: ', $scope.inventory_type)
            if ($scope.inventory_type == 'properties') {
              $scope.matched_buildings = data.properties.matched;
              $scope.unmatched_buildings = data.properties.unmatched;
            } else {
              $scope.matched_buildings = data.tax_lots.matched;
              $scope.unmatched_buildings = data.tax_lots.unmatched;
            }
          });
      };

      /**
       * back_to_list: shows the matching list table, hides the matching detail
       *   table
       */
      $scope.back_to_list = function () {
        $scope.show_building_list = true;
      };

      /*
       * order_by_field: toggle between ordering table rows in ascending or descending order of field value
       */

      $scope.order_by_field = function (field, reverse) {
        $scope.inventory = order_by($scope.inventory, field, reverse);
      };

      $scope.cycleChanged = function () {
        var initial = _.isUndefined($scope.import_files);
        $scope.import_files = _.filter($scope.import_files.dataset.importfiles, function (file) {
          return file.cycle == $scope.selectedCycle.id;
        });
        if (!initial) {
          // If not first load, default to the first available file in the newly selected cycle
          $scope.file_select.file = _.head($scope.import_files);
          $scope.fileChanged();
        }
      };

      $scope.fileChanged = function () {
        $state.go('matching', {importfile_id: $scope.file_select.file.id});
      };

      /**
       * init: sets the default pagination, gets the columns that should be displayed
       *   in the matching list table, sets the table inventory from the inventory_payload
       */
      $scope.init = function () {
        $scope.cycleChanged();
        $scope.columns = search_service.generate_columns($scope.fields, $scope.default_columns);
        $scope.number_properties_matching_search = inventory_payload.number_properties_matching_search;
        $scope.number_tax_lots_matching_search = inventory_payload.number_tax_lots_matching_search;
        $scope.number_properties_returned = inventory_payload.number_properties_returned;
        $scope.number_tax_lots_returned = inventory_payload.number_tax_lots_returned;

        if ($scope.inventory_type == 'properties') {
          $scope.inventory = inventory_payload.properties;
          $scope.num_pages = Math.ceil(inventory_payload.number_properties_matching_search / $scope.number_per_page);
        } else {
          $scope.inventory = inventory_payload.tax_lots;
          $scope.num_pages = Math.ceil(inventory_payload.number_tax_lots_matching_search / $scope.number_per_page);
        }
        update_start_end_paging();

        $scope.update_number_matched();
      };
      $scope.init();
    }]);
