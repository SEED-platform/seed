/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching_list', [])
  .controller('matching_list_controller', [
    '$scope',
    '$log',
    '$window',
    '$state',
    '$stateParams',
    'import_file_payload',
    'inventory_payload',
    'columns',
    'cycles',
    'matching_service',
    'inventory_service',
    'naturalSort',
    'spinner_utility',
    'Notification',
    function ($scope,
              $log,
              $window,
              $state,
              $stateParams,
              import_file_payload,
              inventory_payload,
              columns,
              cycles,
              matching_service,
              inventory_service,
              naturalSort,
              spinner_utility,
              Notification) {
      spinner_utility.show();
      // Remove import_files that haven't yet been mapped
      _.remove(import_file_payload.import_file.dataset.importfiles, function (importfile) {
        return importfile.mapping_done !== true;
      });

      $scope.import_file = import_file_payload.import_file;
      $scope.inventory_type = $stateParams.inventory_type;

      var validCycles = _.uniq(_.map(import_file_payload.import_file.dataset.importfiles, 'cycle'));
      $scope.cycles = _.filter(cycles.cycles, function (cycle) {
        return _.includes(validCycles, cycle.id);
      });
      $scope.selectedCycle = _.find($scope.cycles, {id: $scope.import_file.cycle});
      $scope.inventory = $scope.inventory_type === 'properties' ? inventory_payload.properties : inventory_payload.tax_lots;
      $scope.filtered = [];
      $scope.number_per_page_options = [5, 10, 25, 50, 100];
      $scope.number_per_page = inventory_service.loadMatchesPerPage();
      if (!_.includes($scope.number_per_page_options, $scope.number_per_page)) $scope.number_per_page = 25;
      $scope.current_page = 0;
      $scope.number_of_pages = 1;
      $scope.order_by = '';
      $scope.sort_reverse = false;
      $scope.showing = {};
      $scope.selectedFile = $scope.import_file.dataset.importfiles[0];

      // Reduce columns to only the ones that are populated
      $scope.reduced_columns = _.reject(columns, {extraData: true});
      $scope.columns = [];
      var existing_keys = _.pull(_.keys(_.first($scope.inventory)), 'id', 'matched', 'extra_data', 'coparent');
      var existing_extra_keys = _.keys(_.get($scope.inventory, '[0].extra_data', null));
      _.forEach(columns, function (col) {
        if (!col.extraData) {
          if (_.includes(existing_keys, col.name)) $scope.columns.push(col);
        } else {
          if (_.includes(existing_extra_keys, col.name)) $scope.columns.push(col);
        }
      });

      $scope.SHOW_ALL = 'Show All';
      $scope.SHOW_MATCHED = 'Show Matched';
      $scope.SHOW_UNMATCHED = 'Show Unmatched';

      $scope.filter_options = [$scope.SHOW_ALL, $scope.SHOW_MATCHED, $scope.SHOW_UNMATCHED];
      $scope.selectedFilter = $scope.SHOW_ALL;

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
        inventory_service.saveMatchesPerPage($scope.number_per_page);
      };

      var refresh = function () {
        spinner_utility.show();
        return $scope.update_number_matched().then(function () {
          spinner_utility.hide();
        });
      };

      $scope.unmatch = function (inventory) {
        return matching_service.unmatch($scope.import_file.id, $scope.inventory_type, inventory.id, inventory.coparent.id).then(function () {
          delete inventory.coparent;
          Notification.success('Successfully unmerged ' + ($scope.inventory_type === 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        }, function (err) {
          $log.error(err);
          inventory.matched = true;
          Notification.error('Failed to unmerge ' + ($scope.inventory_type === 'properties' ? 'properties' : 'tax lots'));
          return refresh();
        });
      };

      /**
       * update_number_matched: updates the number of matched and unmatched
       *   buildings
       */
      $scope.update_number_matched = function () {
        if (!_.has($scope, 'unmatched_buildings')) {
          $scope.matched_buildings = _.filter($scope.inventory, 'matched').length;
          $scope.unmatched_buildings = $scope.inventory.length - $scope.matched_buildings;
        } else {
          return inventory_service.get_matching_status($scope.selectedFile.id, $scope.inventory_type).then(function (data) {
            var unmatched_ids;
            if ($scope.inventory_type === 'properties') {
              $scope.matched_buildings = data.properties.matched;
              $scope.unmatched_buildings = data.properties.unmatched;
              unmatched_ids = data.properties.unmatched_ids;
            } else {
              $scope.matched_buildings = data.tax_lots.matched;
              $scope.unmatched_buildings = data.tax_lots.unmatched;
              unmatched_ids = data.tax_lots.unmatched_ids;
            }
            // Check that no other rows became unmatched
            _.forEach($scope.inventory, function (i) {
              if (_.includes(unmatched_ids, i.id)) {
                i.matched = false;
                delete i.coparent;
              }
            });
          });
        }
      };

      // Sort by Columns Ascending and Descending
      $scope.sortColumn = 'name';
      $scope.reverseSort = false;

      $scope.sortData = function (column, extraData) {
        _.defer(spinner_utility.show);
        _.delay(function () {
          $scope.$apply(function () {
            if (extraData) column = 'extra_data[\'' + column + '\']';
            if ($scope.sortColumn === column && $scope.reverseSort) {
              $scope.reverseSort = false;
              $scope.sortColumn = 'name';
            } else {
              $scope.reverseSort = $scope.sortColumn === column ? !$scope.reverseSort : false;
              $scope.sortColumn = column;
            }

            spinner_utility.hide();
          });
        }, 50);
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

      // Custom filter
      $scope.allSearch = function (row) {
        var i, searchText, searchTextLower, rowValue, reducedColLower, isMatch;
        for (i = 0; i < $scope.columns.length; i++) {
          searchText = $scope.columns[i].searchText;
          rowValue = $scope.columns[i].extraData ? row.extra_data[$scope.columns[i].name] : row[$scope.columns[i].name];
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

      $scope.cycleChanged = function () {
        var initial = _.isUndefined($scope.import_files);
        $scope.import_files = _.filter($scope.import_file.dataset.importfiles, function (file) {
          return file.cycle === _.get($scope.selectedCycle, 'id');
        });
        if (!initial) {
          // If not first load, default to the first available file in the newly selected cycle
          $scope.selectedFile = _.head($scope.import_files);
          $scope.fileChanged();
        }
      };

      $scope.fileChanged = function () {
        $state.go('matching_list', {importfile_id: $scope.selectedFile.id, inventory_type: $scope.inventory_type});
      };

      $scope.$watch('filtered', _.debounce(function(newValue, oldValue) {
        if (newValue === [] && oldValue === []) return;
        $scope.update_start_end_paging();
      }), 10);

      /**
       * init: sets the default pagination, gets the columns that should be displayed
       *   in the matching list table, sets the table inventory from the inventory_payload
       */
      $scope.init = function () {
        $scope.cycleChanged();
        $scope.update_number_matched();

        _.delay(spinner_utility.hide, 150);
      }();
    }]);
