/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching_detail', [])
  .controller('matching_detail_controller', [
    '$scope',
    '$log',
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
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.state_id = $stateParams.state_id;
      $scope.available_matches = available_matches.states;

      $scope.state = state_payload.state;
      $scope.filtered = [];
      $scope.number_per_page_options = [5, 10, 25, 50, 100];
      $scope.number_per_page = inventory_service.loadDetailMatchesPerPage();
      if (!_.includes($scope.number_per_page_options, $scope.number_per_page)) $scope.number_per_page = 25;
      $scope.current_page = 0;
      $scope.number_of_pages = 1;
      $scope.order_by = '';
      $scope.sort_reverse = false;
      $scope.showing = {};

      $scope.columns = columns;
      $scope.reduced_columns = _.reject(columns, {extraData: true});

      /**
       * Pagination code
       */
      $scope.update_start_end_paging = function () {
        $scope.number_of_pages = Math.max(Math.ceil($scope.filtered.length / $scope.number_per_page), 1);
        $scope.current_page = _.min([$scope.current_page, $scope.number_of_pages - 1]);

        _.defer(function () {
          $scope.$apply(function () {
            $scope.showing.total = $scope.filtered.length;
            if ($scope.showing.total === 0) {
              $scope.showing.start = 0;
              $scope.showing.end = 0;
            } else {
              $scope.showing.start = $scope.current_page * $scope.number_per_page + 1;
              $scope.showing.end = Math.min($scope.showing.start + $scope.number_per_page - 1, $scope.showing.total);
            }
          });
        });
      };

      $scope.save_number_per_page = function () {
        inventory_service.saveDetailMatchesPerPage($scope.number_per_page);
      };

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
        return inventory_service.search_matching_inventory($scope.import_file.id, {
          get_coparents: true,
          inventory_type: $scope.inventory_type,
          state_id: $stateParams.state_id
        }).then(function (data) {
          $scope.state = data.state;
        }).then(function () {
          return matching_service.available_matches($scope.import_file.id, $scope.inventory_type, $scope.state_id).then(function (data) {
            $scope.available_matches = data.states;
            spinner_utility.hide();
          });
        });
      };

      $scope.unmatch = function () {
        return matching_service.unmatch($scope.import_file.id, $scope.inventory_type, $scope.state_id, $scope.state.coparent.id).then(function () {
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
        return matching_service.match($scope.import_file.id, $scope.inventory_type, $scope.state_id, state.id).then(function () {
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

      $scope.$watch('filtered', _.debounce(function(newValue, oldValue) {
        if (newValue === [] && oldValue === []) return;
        $scope.update_start_end_paging();
      }), 10);

      _.delay(spinner_utility.hide, 150);
    }]);
