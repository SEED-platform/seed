/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.show_populated_columns_modal', [])
  .controller('show_populated_columns_modal_controller', [
    '$scope',
    '$window',
    '$uibModalInstance',
    'Notification',
    'inventory_service',
    'modified_service',
    'spinner_utility',
    'columns',
    'currentProfile',
    'cycle',
    'provided_inventory',
    'inventory_type',
    function ($scope, $window, $uibModalInstance, Notification, inventory_service, modified_service, spinner_utility, columns, currentProfile, cycle, provided_inventory, inventory_type) {
      $scope.columns = columns;
      $scope.currentProfile = currentProfile;
      $scope.cycle = cycle;
      $scope.inventory_type = inventory_type;

      _.forEach($scope.columns, function (col) {
        col.pinnedLeft = false;
        col.visible = true;
      });

      var notEmpty = function (value) {
        return !_.isNil(value) && value !== '';
      };

      var fetch = function (page, chunk) {
        var fn;
        if ($scope.inventory_type === 'properties') {
          fn = inventory_service.get_properties;
        } else if ($scope.inventory_type === 'taxlots') {
          fn = inventory_service.get_taxlots;
        }
        return fn(page, chunk, $scope.cycle, -1).then(function (data) {
          $scope.progress = Math.round(data.pagination.end / data.pagination.total * 100);
          if (data.pagination.has_next) {
            return fetch(page + 1, chunk).then(function (data2) {
              return data.results.concat(data2);
            });
          }
          return data.results;
        });
      };

      var update_profile_with_populated_columns = function (inventory) {
        $scope.status = 'Processing ' + $scope.columns.length + ' columns in ' + inventory.length + ' records';

        var cols = _.reject($scope.columns, 'related');
        // console.log('cols', cols);

        var relatedCols = _.filter($scope.columns, 'related');
        // console.log('relatedCols', relatedCols);

        var col_key = provided_inventory ? 'column_name' : 'name';

        _.forEach(inventory, function (record, index) {
          // console.log(cols.length + ' remaining cols to check');
          _.forEachRight(cols, function (col, colIndex) {
            if (notEmpty(record[col[col_key]])) {
              // console.log('Removing ' + col[col_key] + ' from cols');
              cols.splice(colIndex, 1);
            }
          });

          _.forEach(record.related, function (relatedRecord) {
            // console.log(relatedCols.length + ' remaining related cols to check');
            _.forEachRight(relatedCols, function (col, colIndex) {
              if (notEmpty(relatedRecord[col[col_key]])) {
                // console.log('Removing ' + col[col_key] + ' from relatedCols');
                relatedCols.splice(colIndex, 1);
              }
            });
          });

          $scope.progress = index / inventory.length * 50 + 50;
        });

        // determine hidden columns
        var visible = _.reject($scope.columns, function (col) {
          if (!col.related) {
            return _.find(cols, {id: col.id});
          }
          return _.find(relatedCols, {id: col.id});
        });

        var hidden = _.reject($scope.columns, function (col) {
          return _.find(visible, {id: col.id});
        });

        _.forEach(hidden, function (col) {
          col.visible = false;
        });

        var columns = [];
        _.forEach(visible, function (col) {
          columns.push({
            column_name: col.column_name,
            id: col.id,
            order: columns.length + 1,
            pinned: col.pinnedLeft,
            table_name: col.table_name
          });
        });

        var id = $scope.currentProfile.id;
        var profile = _.omit($scope.currentProfile, 'id');
        profile.columns = columns;
        inventory_service.update_column_list_profile(id, profile).then(function (/*updatedProfile*/) {
          modified_service.resetModified();
          $scope.progress = 100;
          $scope.state = 'done';
          $scope.status = 'Found ' + visible.length + ' populated columns';
        });
      };

      $scope.start = function () {
        $scope.state = 'running';
        $scope.status = 'Fetching Inventory';

        if (provided_inventory) {
          update_profile_with_populated_columns(provided_inventory);
        } else {
          var page = 1;
          var chunk = 5000;
          fetch(page, chunk).then(update_profile_with_populated_columns);
        }
      };

      $scope.refresh = function () {
        spinner_utility.show();
        $window.location.reload();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
