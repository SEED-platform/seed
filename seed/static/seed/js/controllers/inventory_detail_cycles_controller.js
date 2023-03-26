/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_cycles', [])
  .controller('inventory_detail_cycles_controller', [
    '$scope',
    '$filter',
    '$stateParams',
    '$window',
    'cycles',
    'spinner_utility',
    'inventory_service',
    'inventory_payload',
    'columns',
    'profiles',
    'current_profile',
    'organization_payload',
    function (
      $scope,
      $filter,
      $stateParams,
      $window,
      cycles,
      spinner_utility,
      inventory_service,
      inventory_payload,
      columns,
      profiles,
      current_profile,
      organization_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      $scope.states = inventory_payload.data;
      $scope.base_state = _.find(inventory_payload.data, {view_id: $stateParams.view_id});

      $scope.cycles = _.reduce(cycles.cycles, function (cycles_by_id, cycle) {
        cycles_by_id[cycle.id] = cycle;
        return cycles_by_id;
      }, {});

      $scope.organization = organization_payload.organization;

      // Flag columns whose values have changed between cycles.
      var changes_check = function (column) {
        var uniq_column_values;

        if (column.is_extra_data) {
          uniq_column_values = _.uniqBy($scope.states, function (state) {
            return state.extra_data[column.column_name];
          });
        } else {
          uniq_column_values = _.uniqBy($scope.states, column.column_name);
        }

        column.changed = uniq_column_values.length > 1;
        return column;
      };

      // Detail Column List Profile
      $scope.profiles = profiles;
      $scope.currentProfile = current_profile;

      if ($scope.currentProfile) {
        $scope.columns = [];
        _.forEach($scope.currentProfile.columns, function (col) {
          var foundCol = _.find(columns, {id: col.id});
          if (foundCol) $scope.columns.push(changes_check(foundCol));
        });
      } else {
        // No profiles exist
        $scope.columns = _.map(_.reject(columns, 'is_extra_data'), function (col) {
          return changes_check(col);
        });
      }

      var ignoreNextChange = true;
      $scope.$watch('currentProfile', function (newProfile) {
        if (ignoreNextChange) {
          ignoreNextChange = false;
          return;
        }

        inventory_service.save_last_detail_profile(newProfile.id, $scope.inventory_type);
        spinner_utility.show();
        $window.location.reload();
      });

      // Horizontal scroll for "2 tables" that scroll together for fixed header effect.
      var table_container = $('.table-xscroll-fixed-header-container');

      table_container.scroll(function () {
        $('.table-xscroll-fixed-header-container > .table-body-x-scroll').width(
          table_container.width() + table_container.scrollLeft()
        );
      });

      $scope.inventory_display_name = function (property_type) {
        let error = '';
        let field = property_type == 'property' ? $scope.organization.property_display_field : $scope.organization.taxlot_display_field;
        if (!(field in $scope.base_state)) {
          error = field + ' does not exist';
          field = 'address_line_1';
        }
        if (!$scope.base_state[field]) {
          error += (error == '' ? '' : ' and default ') + field + ' is blank';
        }
        $scope.inventory_name = $scope.base_state[field] ? $scope.base_state[field] : '(' + error + ') <i class="glyphicon glyphicon-question-sign" title="This can be changed from the organization settings page."></i>';
      };

      $scope.displayValue = function (dataType, value) {
        if (dataType === 'datetime') {
          return $filter('date')(value, 'yyyy-MM-dd h:mm a');
        } else if (['area', 'eui', 'float', 'number'].includes(dataType)) {
          return $filter('number')(value, $scope.organization.display_decimal_places);
        }
        return value;
      };

    }]);
