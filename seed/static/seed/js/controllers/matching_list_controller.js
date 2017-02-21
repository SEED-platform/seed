/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching_list', [])
  .controller('matching_list_controller', [
    '$scope',
    '$state',
    '$stateParams',
    'import_file_payload',
    'inventory_payload',
    'building_services',
    'columns',
    'cycles',
    'urls',
    '$uibModal',
    'search_service',
    'matching_service',
    'inventory_service',
    'naturalSort',
    'spinner_utility',
    function ($scope,
              $state,
              $stateParams,
              import_file_payload,
              inventory_payload,
              building_services,
              columns,
              cycles,
              urls,
              $uibModal,
              search_service,
              matching_service,
              inventory_service,
              naturalSort,
              spinner_utility) {
      spinner_utility.show();
      // Remove import_files that haven't yet been mapped
      _.remove(import_file_payload.import_file.dataset.importfiles, function (importfile) {
        return importfile.mapping_done !== true;
      });

      $scope.search = angular.copy(search_service);
      $scope.search.url = urls.search_buildings;

      $scope.import_file = import_file_payload.import_file;
      var validCycles = _.uniq(_.map(import_file_payload.import_file.dataset.importfiles, 'cycle'));
      $scope.cycles = _.filter(cycles.cycles, function (cycle) {
        return _.includes(validCycles, cycle.id);
      });
      $scope.selectedCycle = _.find($scope.cycles, {id: $scope.import_file.cycle});

      $scope.inventory = [];
      $scope.number_per_page = 10;
      $scope.current_page = 1;
      $scope.order_by = '';
      $scope.sort_reverse = false;
      $scope.number_properties_matching_search = 0;
      $scope.number_tax_lots_matching_search = 0;
      $scope.number_properties_returned = 0;
      $scope.number_tax_lots_returned = 0;
      $scope.pagination = {};
      $scope.showing = {};
      $scope.pagination.number_per_page_options = [10, 25, 50, 100];
      $scope.pagination.number_per_page_options_model = 10;
      $scope.columns = [];
      $scope.alerts = [];
      $scope.file_select = {
        file: $scope.import_file.dataset.importfiles[0]
      };
      $scope.importfile_id = $stateParams.importfile_id;
      $scope.inventory_type = $stateParams.inventory_type;

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
        console.debug('filter_search called');
        $scope.update_number_matched();
        inventory_service.search_matching_inventory($scope.file_select.file.id)
          .then(function (data) {
            // safe-guard against future init() calls
            inventory_payload = data;

            if ($scope.inventory_type == 'properties') {
              $scope.inventory = data.properties;
              $scope.num_pages = Math.ceil(data.number_properties_matching_search / $scope.number_per_page);
            } else {
              $scope.inventory = data.tax_lots;
              $scope.num_pages = Math.ceil(data.number_tax_lots_matching_search / $scope.number_per_page);
            }
            $scope.number_properties_matching_search = data.number_properties_matching_search;
            $scope.number_tax_lots_matching_search = data.number_tax_lots_matching_search;
            $scope.number_properties_returned = data.number_properties_returned;
            $scope.number_tax_lots_returned = data.number_tax_lots_returned;
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

      $scope.SHOW_ALL = 'Show All';
      $scope.SHOW_MATCHED = 'Show Matched';
      $scope.SHOW_UNMATCHED = 'Show Unmatched';

      $scope.filter_options = [$scope.SHOW_ALL, $scope.SHOW_MATCHED, $scope.SHOW_UNMATCHED];

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

      $scope.unmatch = function (inventory) {
        console.debug('Unmatch called for ' + inventory.id);
        // var source, target, create;
        // if (building.coparent && building.coparent.id) {
        //   if (building.matched) {
        //     source = building.id;
        //     target = building.coparent.id;
        //   } else {
        //     source = building.coparent.id;
        //     target = building.id;
        //   }
        //   create = building.matched;
        // } else {
        //   building.matched = false;
        //   return;
        // }
        //
        // // creates or removes a match
        // var save_promise = null;
        // if ($scope.inventory_type == 'properties') save_promise = inventory_service.save_property_match(source, target, create);
        // else save_promise = inventory_service.save_taxlot_match(source, target, create);
        // save_promise.then(function (data) {
        //   // update building and coparent's child in case of a unmatch
        //   // without a page refresh
        //   if (building.matched) {
        //     building.children = building.children || [0];
        //     building.children[0] = data.child_id;
        //   }
        //   $scope.update_number_matched();
        //   $scope.$emit('finished_saving');
        // }, function (data, status) {
        //   building.matched = !building.matched;
        //   $scope.$emit('finished_saving');
        // });
      };

      /**
       * open_edit_columns_modal: opens the edit columns modal to select and set
       *   the columns used in the matching list table and matching detail table
       */
      // $scope.open_edit_columns_modal = function () {
      //   var modalInstance = $uibModal.open({
      //     templateUrl: urls.static_url + 'seed/partials/custom_view_modal.html',
      //     controller: 'buildings_settings_controller',
      //     resolve: {
      //       shared_fields_payload: function () {
      //         return {show_shared_buildings: false};
      //       },
      //       project_payload: function () {
      //         return {project: {}};
      //       },
      //       building_payload: function () {
      //         return {building: {}};
      //       }
      //     }
      //   });
      // };


      /**
       * update_number_matched: updates the number of matched and unmatched
       *   buildings
       */
      $scope.update_number_matched = function () {
        building_services.get_matching_results($scope.file_select.file.id)
          .then(function (data) {
            if ($scope.inventory_type == 'properties') {
              $scope.matched_buildings = data.properties.matched;
              $scope.unmatched_buildings = data.properties.unmatched;
            } else {
              $scope.matched_buildings = data.tax_lots.matched;
              $scope.unmatched_buildings = data.tax_lots.unmatched;
            }
          });
      };

      /*
       * order_by_field: toggle between ordering table rows in ascending or descending order of field value
       */

      $scope.order_by_field = function (is_extra_data, field) {
        if ($scope.order_by != field) {
          $scope.sort_reverse = false;
        } else {
          $scope.sort_reverse = !$scope.sort_reverse;
        }
        $scope.order_by = field;
        $scope.inventory = $scope.inventory.sort(function (a, b) {
          if (!$scope.sort_reverse) return is_extra_data ? naturalSort(a.extra_data[field], b.extra_data[field]) : naturalSort(a[field], b[field]);
          else return is_extra_data ? naturalSort(b.extra_data[field], a.extra_data[field]) : naturalSort(b[field], a[field]);
        });
      };

      $scope.cycleChanged = function () {
        var initial = _.isUndefined($scope.import_files);
        $scope.import_files = _.filter($scope.import_file.dataset.importfiles, function (file) {
          return file.cycle == _.get($scope.selectedCycle, 'id');
        });
        if (!initial) {
          // If not first load, default to the first available file in the newly selected cycle
          $scope.file_select.file = _.head($scope.import_files);
          $scope.fileChanged();
        }
      };

      $scope.fileChanged = function () {
        $state.go('matching_list', {importfile_id: $scope.file_select.file.id});
      };

      /**
       * init: sets the default pagination, gets the columns that should be displayed
       *   in the matching list table, sets the table inventory from the inventory_payload
       */
      $scope.init = function () {
        $scope.cycleChanged();
        // $scope.columns = search_service.generate_columns($scope.fields, $scope.default_columns);
        $scope.columns = columns;
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

        _.delay(function () {
          spinner_utility.hide();
        }, 150);
      };
      $scope.init();
    }]);
