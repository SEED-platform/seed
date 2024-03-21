/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.column_settings', []).controller('column_settings_controller', [
  '$scope',
  '$q',
  '$state',
  '$stateParams',
  '$uibModal',
  'Notification',
  'all_columns',
  'columns',
  'organization_payload',
  'auth_payload',
  'columns_service',
  'modified_service',
  'spinner_utility',
  'urls',
  'naturalSort',
  '$translate',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $q,
    $state,
    $stateParams,
    $uibModal,
    Notification,
    all_columns,
    columns,
    organization_payload,
    auth_payload,
    columns_service,
    modified_service,
    spinner_utility,
    urls,
    naturalSort,
    $translate
  ) {
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.state = $state.current;

    const originalColumns = angular.copy(columns);
    $scope.columns = columns;
    const initial_matching_ids = columns.reduce((acc, cur) => {
      cur.is_matching_criteria && acc.push(cur.id);
      return acc;
    }, []);
    let diff = {};

    $scope.filter_params = {};
    $scope.btnText = 'Collapse Help';

    $scope.data_types = [
      { id: 'None', label: '' },
      { id: 'number', label: $translate.instant('Number') },
      { id: 'float', label: $translate.instant('Float') },
      { id: 'integer', label: $translate.instant('Integer') },
      { id: 'string', label: $translate.instant('Text') },
      { id: 'datetime', label: $translate.instant('Datetime') },
      { id: 'date', label: $translate.instant('Date') },
      { id: 'boolean', label: $translate.instant('Boolean') },
      { id: 'area', label: $translate.instant('Area') },
      { id: 'eui', label: $translate.instant('EUI') },
      { id: 'geometry', label: $translate.instant('Geometry') },
      { id: 'ghg', label: $translate.instant('GHG') },
      { id: 'ghg_intensity', label: $translate.instant('GHG Intensity') }
    ];

    $scope.comstock_types = [
      { id: null, label: '' },
      { id: 'division', label: $translate.instant('comstock.division') },
      { id: 'hvac_system_type', label: $translate.instant('comstock.hvac_system_type') },
      { id: 'rentable_area', label: $translate.instant('comstock.rentable_area') },
      { id: 'number_of_stories', label: $translate.instant('comstock.number_of_stories') },
      { id: 'year_built', label: $translate.instant('comstock.year_built') },
      { id: 'weekend_start_time', label: $translate.instant('comstock.weekend_start_time') },
      { id: 'weekend_duration', label: $translate.instant('comstock.weekend_duration') },
      { id: 'weekday_start_time', label: $translate.instant('comstock.weekday_start_time') },
      { id: 'weekday_duration', label: $translate.instant('comstock.weekday_duration') },
      { id: 'building_shape', label: $translate.instant('comstock.building_shape') },
      { id: 'built_code', label: $translate.instant('comstock.built_code') },
      { id: 'rotation', label: $translate.instant('comstock.rotation') },
      { id: 'aspect_ratio', label: $translate.instant('comstock.aspect_ratio') },
      { id: 'building_type', label: $translate.instant('comstock.building_type') },
      { id: 'state', label: $translate.instant('comstock.state') },
      { id: 'county', label: $translate.instant('comstock.county') },
      { id: 'climate_zone', label: $translate.instant('comstock.climate_zone') }
    ];

    $scope.changeText = (btnText) => {
      if (btnText === 'Collapse Help') {
        $scope.btnText = 'Expand Help';
      } else {
        $scope.btnText = 'Collapse Help';
      }
    };
    $scope.change_merge_protection = (column) => {
      // Keep geocoding results columns aligned in merge protection settings
      const change_to = column.merge_protection === 'Favor New' ? 'Favor Existing' : 'Favor New';

      const geocoding_results_columns = ['geocoding_confidence', 'longitude', 'latitude'];
      if (geocoding_results_columns.includes(column.column_name)) {
        geocoding_results_columns.forEach((geo_col) => {
          _.find($scope.columns, { column_name: geo_col }).merge_protection = change_to;
        });
      } else {
        column.merge_protection = change_to;
      }

      $scope.setModified();
    };

    $scope.change_is_matching_criteria = (column) => {
      column.is_matching_criteria = !column.is_matching_criteria;
      $scope.setModified();
    };

    $scope.matching_status = (column) => {
      if (column.is_extra_data) return 'ineligible';
      if ($scope.org.inventory_count && initial_matching_ids.includes(column.id)) return 'locked';
      return 'eligible';
    };

    $scope.change_recognize_empty = (column) => {
      column.recognize_empty = !column.recognize_empty;
      $scope.setModified();
    };

    // Separate array used to capture and track geocoding-enabled columns and their order
    // Any change to the array leading to position switching should be followed by a
    // recalculation of geocoding_order values using indices.
    $scope.geocoding_columns = _.orderBy(
      _.filter(columns, (column) => column.geocoding_order > 0),
      'geocoding_order'
    );

    $scope.geocoding_columns_position_options = _.range(1, $scope.geocoding_columns.length + 1, 1);

    const update_geocoding_order_values = () => {
      // Since array order represents geocoding order, use indices to update geocoding_order values
      _.each($scope.geocoding_columns, (geocode_active_col, index) => {
        geocode_active_col.geocoding_order = index + 1;
      });
    };

    const remove_geocoding_col_by_name = (column) => {
      _.remove($scope.geocoding_columns, (included_col) => included_col.name === column.name);
    };

    const set_modified_and_check_sort = () => {
      $scope.setModified();
      if ($scope.column_sort === 'geocoding_order') {
        geocoding_order_sort();
      }
    };

    $scope.geocoding_toggle = (column) => {
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

    $scope.reinsert_geocoding_column = (column) => {
      remove_geocoding_col_by_name(column);
      $scope.geocoding_columns.splice(column.geocoding_order - 1, 0, column);
      update_geocoding_order_values();
      set_modified_and_check_sort();
    };

    $scope.comstockModified = (column) => {
      // Remove any potential duplicates
      if (column.comstock_mapping !== null) {
        _.forEach($scope.columns, (col) => {
          // eslint-disable-next-line lodash/prefer-matches
          if (col.id !== column.id && col.comstock_mapping === column.comstock_mapping) {
            col.comstock_mapping = null;
          }
        });
      }
      $scope.setModified();
    };

    $scope.setModified = () => {
      $scope.columns_updated = false;
      updateDiff();
      if (_.isEmpty(diff)) {
        modified_service.resetModified();
      } else {
        modified_service.setModified();
      }
    };

    $scope.isModified = () => modified_service.isModified();

    var updateDiff = () => {
      diff = {};

      const cleanColumns = angular.copy(columns);
      _.forEach(originalColumns, (originalCol, index) => {
        if (!_.isEqual(originalCol, cleanColumns[index])) {
          const modifiedKeys = _.reduce(originalCol, (result, value, key) => (_.isEqual(value, cleanColumns[index][key]) ? result : result.concat(key)), []);
          diff[originalCol.id] = _.pick(cleanColumns[index], modifiedKeys);
        }
      });
    };

    // Table Sorting
    const default_sort_toggle = () => {
      $scope.column_sort = 'default';
      $scope.columns = _.sortBy($scope.columns, 'id');
    };

    default_sort_toggle();

    const display_name_order_sort = () => {
      $scope.columns = _.sortBy($scope.columns, 'displayName');
    };

    $scope.toggle_display_name_order_sort = () => {
      if ($scope.column_sort !== 'display_name_order') {
        display_name_order_sort();
        $scope.column_sort = 'display_name_order';
      } else {
        default_sort_toggle();
      }
    };

    const column_name_order_sort = () => {
      $scope.columns = _.sortBy($scope.columns, 'name');
    };

    $scope.toggle_column_name_order_sort = () => {
      if ($scope.column_sort !== 'column_name_order') {
        column_name_order_sort();
        $scope.column_sort = 'column_name_order';
      } else {
        default_sort_toggle();
      }
    };

    var geocoding_order_sort = () => {
      $scope.columns = _.sortBy(
        $scope.columns,
        (col) =>
          // infinity at 0, increasing after
          1 / col.geocoding_order + col.geocoding_order
      );
    };

    $scope.toggle_geocoding_order_sort = () => {
      if ($scope.column_sort !== 'geocoding_order') {
        geocoding_order_sort();
        $scope.column_sort = 'geocoding_order';
      } else {
        default_sort_toggle();
      }
    };

    $scope.toggle_recognize_empty_sort = () => {
      if ($scope.column_sort !== 'recognize_empty') {
        $scope.columns = _.orderBy($scope.columns, 'recognize_empty', 'desc');

        $scope.column_sort = 'recognize_empty';
      } else {
        default_sort_toggle();
      }
    };

    $scope.toggle_matching_criteria_sort = () => {
      if ($scope.column_sort !== 'is_matching_criteria') {
        $scope.columns = _.sortBy($scope.columns, (col) => {
          if (col.is_matching_criteria) {
            return 0;
          }
          if (col.is_extra_data) {
            return 2;
          }
          return 1;
        });
        $scope.column_sort = 'is_matching_criteria';
      } else {
        default_sort_toggle();
      }
    };

    const column_update_complete = (match_link_summary) => {
      $scope.columns_updated = true;
      const diff_count = _.keys(diff).length;
      Notification.success(`Successfully updated ${diff_count} column${diff_count === 1 ? '' : 's'}`);

      if (match_link_summary) {
        _.forOwn(match_link_summary, (state_summary, state) => {
          let type;
          if (state === 'PropertyState') {
            type = 'Property';
          } else {
            type = 'TaxLot';
          }

          const { merged_count } = state_summary;
          const { linked_sets_count } = state_summary;

          if (merged_count) {
            Notification.info({
              message: `${type} merge count: ${merged_count}`,
              delay: 10000
            });
          }
          if (linked_sets_count) {
            Notification.info({
              message: `${type} linked sets count: ${linked_sets_count}`,
              delay: 10000
            });
          }
        });
      }

      modified_service.resetModified();
      $state.reload();
    };

    // Saves the modified columns
    $scope.save_settings = () => {
      $scope.columns_updated = false;

      if (_.filter($scope.columns, 'is_matching_criteria').length === 0) {
        Notification.error('Error: There must be at least one matching criteria column.');
        return;
      }

      const missingDisplayNames = _.filter(columns, { displayName: undefined });
      if (missingDisplayNames.length) {
        Notification.error(`Error: ${missingDisplayNames.length} required display name${missingDisplayNames.length > 1 ? 's are' : ' is'} empty`);
        return;
      }

      const modal_instance = $scope.open_confirm_column_settings_modal();
      modal_instance.result
        .then(() => {
          // User confirmed
          const promises = [];
          _.forOwn(diff, (delta, column_id) => {
            column_id = Number(column_id);
            const col = angular.copy(_.find($scope.columns, { id: column_id }));
            col.display_name = col.displayName; // Add display_name for backend
            delete col.displayName;
            promises.push(columns_service.update_column_for_org($scope.org.id, column_id, col));
          });

          spinner_utility.show();
          $q.all(promises).then(column_update_complete, (data) => {
            $scope.$emit('app_error', data);
          });
        })
        .catch(() => {
          // User cancelled
        });
    };

    $scope.open_create_column_modal = () => $uibModal.open({
      templateUrl: `${urls.static_url}seed/partials/create_column_modal.html`,
      controller: 'create_column_modal_controller',
      // size: 'lg',
      resolve: {
        org_id: $scope.org.id,
        table_name: () => ($scope.inventory_type === 'properties' ? 'PropertyState' : 'TaxlotState'),
        black_listed_names: () => ['', ...$scope.columns.map((c) => c.column_name)]
      }
    });

    $scope.open_confirm_column_settings_modal = () => $uibModal.open({
      templateUrl: `${urls.static_url}seed/partials/confirm_column_settings_modal.html`,
      controller: 'confirm_column_settings_modal_controller',
      size: 'lg',
      resolve: {
        proposed_changes: () => diff,
        all_columns: () => all_columns,
        columns: () => $scope.columns,
        inventory_type: () => $scope.inventory_type,
        org_id: () => $scope.org.id
      }
    });

    $scope.open_rename_column_modal = (column_id, column_name) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/rename_column_modal.html`,
        controller: 'rename_column_modal_controller',
        resolve: {
          column_id: () => column_id,
          column_name: () => column_name,
          all_column_names: () => _.map($scope.columns, 'column_name'),
          org_id: () => $scope.org.id
        }
      });
    };

    $scope.delete_column = (column) => {
      $uibModal.open({
        backdrop: 'static',
        keyboard: false,
        templateUrl: `${urls.static_url}seed/partials/delete_column_modal.html`,
        controller: 'delete_column_modal_controller',
        resolve: {
          organization_id: () => $scope.org.id,
          column: () => column
        }
      });
    };
  }
]);
