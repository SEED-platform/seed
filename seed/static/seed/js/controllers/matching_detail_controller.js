/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching_detail', [])
  .controller('matching_detail_controller', [
    '$scope',
    '$state',
    '$stateParams',
    'import_file_payload',
    'state_payload',
    'available_matches',
    'columns',
    'urls',
    '$uibModal',
    'search_service',
    'matching_service',
    'inventory_service',
    'spinner_utility',
    'Notification',
    function ($scope,
              $state,
              $stateParams,
              import_file_payload,
              state_payload,
              available_matches,
              columns,
              urls,
              $uibModal,
              search_service,
              matching_service,
              inventory_service,
              spinner_utility,
              Notification) {
      spinner_utility.show();
      $scope.search = angular.copy(search_service);
      $scope.search.url = urls.search_buildings;

      $scope.import_file = import_file_payload.import_file;
      $scope.available_matches = available_matches.states;

      $scope.number_per_page = 10;
      $scope.current_page = 1;
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
      $scope.alerts = [];

      $scope.importfile_id = $stateParams.importfile_id;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.state_id = $stateParams.state_id;

      $scope.columns = columns;
      $scope.state = state_payload.state;

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
        inventory_service.search_matching_inventory($scope.file_select.file.id, {
          get_coparents: true,
          inventory_type: $stateParams.inventory_type,
          state_id: $stateParams.state_id
        }).then(function (data) {
          // safe-guard against future init() calls
          state_payload = data;

          if ($scope.inventory_type == 'properties') {
            $scope.num_pages = Math.ceil(data.number_properties_matching_search / $scope.number_per_page);
          } else {
            $scope.num_pages = Math.ceil(data.number_tax_lots_matching_search / $scope.number_per_page);
          }
          $scope.number_properties_matching_search = data.number_properties_matching_search;
          $scope.number_tax_lots_matching_search = data.number_tax_lots_matching_search;
          $scope.number_properties_returned = data.number_properties_returned;
          $scope.number_tax_lots_returned = data.number_tax_lots_returned;
          update_start_end_paging();
        }).catch(function (data, status) {
          console.log({data: data, status: status});
          $scope.alerts.push({type: 'danger', msg: 'Error searching'});
        });
      };


      $scope.closeAlert = function (index) {
        $scope.alerts.splice(index, 1);
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

      var refresh = function () {
        spinner_utility.show();
        // update state (particularly if coparent)
        return inventory_service.search_matching_inventory($stateParams.importfile_id, {
          get_coparents: true,
          inventory_type: $stateParams.inventory_type,
          state_id: $stateParams.state_id
        }).then(function (data) {
          $scope.state = data.state;
        }).then(function () {
          return matching_service.available_matches($scope.importfile_id, $scope.inventory_type, $scope.state_id).then(function (data) {
            $scope.available_matches = data.states;
            spinner_utility.hide();
          });
        });
      };

      $scope.unmatch = function () {
        return matching_service.unmatch($scope.importfile_id, $scope.inventory_type, $scope.state_id, $scope.state.coparent.id).then(function () {
          delete $scope.state.coparent;
          Notification.success('Successfully unmerged ' + ($scope.inventory_type == 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        }, function (err) {
          console.error(err);
          $scope.state.matched = true;
          Notification.error('Failed to unmerge ' + ($scope.inventory_type == 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        });
      };

      $scope.match = function (state) {
        return matching_service.match($scope.importfile_id, $scope.inventory_type, $scope.state_id, state.id).then(function () {
          Notification.success('Successfully merged ' + ($scope.inventory_type == 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        }, function (err) {
          console.error(err);
          $scope.state.matched = false;
          Notification.error('Failed to merge ' + ($scope.inventory_type == 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        });
      };

      $scope.checkbox_match = function (state) {
        if ($scope.state.matched) {
          var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/unmerge_modal.html',
            controller: 'unmerge_modal_controller',
            resolve: {
              inventory_type: function () {
                return $scope.inventory_type;
              }
            }
          });

          return modalInstance.result.then(function () {
              return $scope.unmatch().then(function () {
                return $scope.match(state);
              });
            }, function () {
              state.checked = false;
            }
          );
        } else {
          return $scope.match(state);
        }
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

      _.delay(function () {
        spinner_utility.hide();
      }, 150);
    }]);
