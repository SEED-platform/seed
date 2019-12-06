/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.column_settings', [])
  .controller('column_settings_controller', [
    '$scope',
    '$q',
    '$state',
    '$stateParams',
    '$uibModal',
    'Notification',
    'columns',
    'organization_payload',
    'auth_payload',
    'columns_service',
    'modified_service',
    'organization_service',
    'spinner_utility',
    'urls',
    'naturalSort',
    'flippers',
    '$translate',
    function (
      $scope,
      $q,
      $state,
      $stateParams,
      $uibModal,
      Notification,
      columns,
      organization_payload,
      auth_payload,
      columns_service,
      modified_service,
      organization_service,
      spinner_utility,
      urls,
      naturalSort,
      flippers,
      $translate
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;

      $scope.state = $state.current;

      var originalColumns = angular.copy(columns);
      $scope.columns = columns;
      var diff = {};

      $scope.filter_params = {};

      $scope.data_types = [
        {id: 'None', label: ''},
        {id: 'number', label: $translate.instant('Number')},
        {id: 'float', label: $translate.instant('Float')},
        {id: 'integer', label: $translate.instant('Integer')},
        {id: 'string', label: $translate.instant('Text')},
        {id: 'datetime', label: $translate.instant('Datetime')},
        {id: 'date', label: $translate.instant('Date')},
        {id: 'boolean', label: $translate.instant('Boolean')},
        {id: 'area', label: $translate.instant('Area')},
        {id: 'eui', label: $translate.instant('EUI')},
        {id: 'geometry', label: $translate.instant('Geometry')}
      ];

      $scope.change_merge_protection = function (column) {
        column.merge_protection = (column.merge_protection === 'Favor New') ? 'Favor Existing' : 'Favor New';
        $scope.setModified();
      };

      $scope.change_is_matching_criteria = function (column) {
        column.is_matching_criteria = !column.is_matching_criteria;
        $scope.setModified();
      };

      // Seperate array used to capture and track geocoding-enabled columns and their order
      // Any change to the array leading to position switching should be followed by a
      // recalulation of geocoding_order values using indeces.
      $scope.geocoding_columns = _.orderBy(
        _.filter(columns, function (column) {
          return column.geocoding_order > 0;
        }),
        'geocoding_order'
      );

      $scope.geocoding_columns_position_options = _.range(1, ($scope.geocoding_columns.length + 1), 1);

      var update_geocoding_order_values = function () {
        // Since array order represents geocoding order, use indeces to update geocoding_order values
        _.each($scope.geocoding_columns, function (geocode_active_col, index) {
          geocode_active_col.geocoding_order = index + 1;
        });
      };

      var remove_geocoding_col_by_name = function (column) {
        _.remove($scope.geocoding_columns, function (included_col) {
          return included_col.name === column.name;
        });
      };

      var set_modified_and_check_sort = function () {
        $scope.setModified();
        if ($scope.column_sort == 'geocoding_order') {
          geocoding_order_sort();
        }
      };

      $scope.geocoding_toggle = function (column) {
        if (column.geocoding_order > 0) {
          // If currently activated, deactivate it and remove from geocoding_columns
          column.geocoding_order = 0;
          remove_geocoding_col_by_name(column);
          update_geocoding_order_values();
        } else {
          // If currently deactivated, activate by adding to geocoding_columns to the end.
          $scope.geocoding_columns.push(column);
          column.geocoding_order = $scope.geocoding_columns.length;
        }
        // Update the count of geocoding columns
        $scope.geocoding_columns_position_options = _.range(1, $scope.geocoding_columns.length + 1, 1);
        set_modified_and_check_sort();
      };

      $scope.reinsert_geocoding_column = function (column) {
        remove_geocoding_col_by_name(column);
        $scope.geocoding_columns.splice((column.geocoding_order - 1), 0, column);
        update_geocoding_order_values();
        set_modified_and_check_sort();
      };

      $scope.setModified = function () {
        $scope.columns_updated = false;
        updateDiff();
        if (_.isEmpty(diff)) {
          modified_service.resetModified();
        } else {
          modified_service.setModified();
        }
      };

      $scope.isModified = function () {
        return modified_service.isModified();
      };

      var updateDiff = function () {
        diff = {};

        var cleanColumns = angular.copy(columns);
        _.forEach(originalColumns, function (originalCol, index) {
          if (!_.isEqual(originalCol, cleanColumns[index])) {
            var modifiedKeys = _.reduce(originalCol, function (result, value, key) {
              return _.isEqual(value, cleanColumns[index][key]) ? result : result.concat(key);
            }, []);
            diff[originalCol.id] = _.pick(cleanColumns[index], modifiedKeys);
            if (_.includes(modifiedKeys, 'displayName')) {
              // Rename to match backend
              diff[originalCol.id].display_name = diff[originalCol.id].displayName;
              delete diff[originalCol.id].displayName;
            }
          }
        });
      };

      // Table Sorting
      var default_sort_toggle = function () {
        $scope.column_sort = 'default';
        $scope.columns = _.sortBy($scope.columns, 'id');
      };

      default_sort_toggle();

      var geocoding_order_sort = function () {
        $scope.columns = _.sortBy($scope.columns, function (col) {
          // infinity at 0, increasing after
          return (1 / col.geocoding_order + col.geocoding_order);
        });
      };

      $scope.toggle_geocoding_order_sort = function () {
        if (($scope.column_sort !== 'geocoding_order')) {
          geocoding_order_sort();
          $scope.column_sort = 'geocoding_order';
        } else {
          default_sort_toggle();
        }
      };

      $scope.toggle_matching_criteria_sort = function () {
        if ($scope.column_sort !== 'is_matching_criteria') {
          $scope.columns = _.reverse(_.sortBy($scope.columns, 'is_matching_criteria'));
          $scope.column_sort = 'is_matching_criteria';
        } else {
          default_sort_toggle();
        }
      };

      // Saves the modified columns
      $scope.save_settings = function () {
        $scope.columns_updated = false;

        if (_.filter($scope.columns, 'is_matching_criteria').length == 0) {
          Notification.error('Error: There must be at least one matching criteria column.');
          return;
        }

        var missingDisplayNames = _.filter(columns, {displayName: undefined});
        if (missingDisplayNames.length) {
          Notification.error('Error: ' + missingDisplayNames.length + ' required display name' + (missingDisplayNames.length > 1 ? 's are' : ' is') + ' empty');
          return;
        }

        var promises = [];
        _.forOwn(diff, function (delta, column_id) {
          promises.push(columns_service.patch_column_for_org($scope.org.id, column_id, delta));
        });

        spinner_utility.show();
        $q.all(promises).then(function (/*results*/) {
          $scope.columns_updated = true;
          modified_service.resetModified();
          var totalChanged = _.keys(diff).length;
          Notification.success('Successfully updated ' + totalChanged + ' column' + (totalChanged === 1 ? '' : 's'));
          $state.reload();
        }, function (data) {
          $scope.$emit('app_error', data);
        }).finally(function () {
          spinner_utility.hide();
        });
      };

      $scope.open_rename_column_modal = function (column_id, column_name) {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/rename_column_modal.html',
          controller: 'rename_column_modal_controller',
          resolve: {
            column_id: function () {
              return column_id;
            },
            column_name: function () {
              return column_name;
            },
            all_column_names: function () {
              return _.map($scope.columns, 'column_name');
            }
          }
        });
      };

    }]);
