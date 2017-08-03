/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching_detail', [])
  .controller('matching_detail_controller', [
    '$scope',
    '$log',
    '$window',
    '$state',
    '$stateParams',
    'naturalSort',
    'import_file_payload',
    'state_payload',
    'available_matches',
    'columns',
    'urls',
    '$uibModal',
    'matching_service',
    'inventory_service',
    'spinner_utility',
    'Notification',
    function ($scope,
              $log,
              $window,
              $state,
              $stateParams,
              naturalSort,
              import_file_payload,
              state_payload,
              available_matches,
              columns,
              urls,
              $uibModal,
              matching_service,
              inventory_service,
              spinner_utility,
              Notification) {
      spinner_utility.show();

      $scope.import_file = import_file_payload.import_file;
      $scope.available_matches = available_matches.states;

      $scope.number_per_page = 10;
      $scope.current_page = 1;
      $scope.pagination = {};
      $scope.prev_page_disabled = false;
      $scope.next_page_disabled = false;
      $scope.showing = {};
      $scope.pagination.number_per_page_options = [10, 25, 50, 100];
      $scope.pagination.number_per_page_options_model = 10;

      $scope.importfile_id = $stateParams.importfile_id;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.state_id = $stateParams.state_id;

      $scope.columns = columns;
      $scope.reduced_columns = _.reject(columns, {extraData: true});
      $scope.state = state_payload.state;

      // Custom filter
      $scope.allSearch = function (row) {
        var i, searchText, searchTextLower, rowValue, reducedColLower, isMatch;
        for (i = 0; i < $scope.reduced_columns.length; i++) {
          searchText = $scope.reduced_columns[i].searchText;
          rowValue = row[$scope.reduced_columns[i].name];
          if (searchText && !_.isNil(rowValue)) {
            // don't return match because it stops the loop, set to variable so even when matches are found, they continue searching(iterating through the loop) when inputs are processed from other columns
            searchTextLower = searchText.toLowerCase();
            reducedColLower = (rowValue + '').toLowerCase();
            isMatch = reducedColLower.indexOf(searchTextLower) > -1;
            // if an item does not match, break the loop
            if (!isMatch) {
              return false;
            }
          } else if (searchText) {
            return false;
          }
        }
        return true;
      };

      // Sort by Columns Ascending and Descending
      $scope.sortColumn = 'name';
      $scope.reverseSort = false;

      $scope.sortData = function (column, extraData) {
        if (extraData) column = 'extra_data[\'' + column + '\']';
        if ($scope.sortColumn === column && $scope.reverseSort) {
          $scope.sortColumn = 'name';
          $scope.reverseSort = false;
        } else {
          $scope.reverseSort = $scope.sortColumn === column ? !$scope.reverseSort : false;
          $scope.sortColumn = column;
        }
      };

      $scope.getSortClass = function (column, extraData) {
        if (extraData) column = 'extra_data[\'' + column + '\']';
        if ($scope.sortColumn === column) {
          return $scope.reverseSort ? 'fa fa-caret-down' : 'fa fa-caret-up';
        }
      };

      $scope.naturalSortComparator = function (a, b) {
        return naturalSort(a.value, b.value);
      };

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
          Notification.success('Successfully unmerged ' + ($scope.inventory_type === 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        }, function (err) {
          $log.error(err);
          $scope.state.matched = true;
          Notification.error('Failed to unmerge ' + ($scope.inventory_type === 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        });
      };

      $scope.match = function (state) {
        return matching_service.match($scope.importfile_id, $scope.inventory_type, $scope.state_id, state.id).then(function () {
          Notification.success('Successfully merged ' + ($scope.inventory_type === 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        }, function (err) {
          $log.error(err);
          $scope.state.matched = false;
          Notification.error('Failed to merge ' + ($scope.inventory_type === 'properties' ? 'properties' : 'tax lots'));
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
          });
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

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section .section_tab_container', '.section .section_header_container', '.matching-tab-container', '.table_footer'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#table-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
      };

      var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
      angular.element($window).on('resize', debouncedHeightUpdate);
      $scope.$on('$destroy', function () {
        angular.element($window).off('resize', debouncedHeightUpdate);
      });

      _.delay(function () {
        spinner_utility.hide();
        $scope.updateHeight();
      }, 150);
    }]);
