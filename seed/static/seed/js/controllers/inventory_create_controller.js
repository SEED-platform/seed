/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.inventory_create', []).controller('inventory_create_controller', [
  '$scope',
  '$state',
  '$stateParams',
  'ah_service',
  'inventory_service',
  'Notification',
  'simple_modal_service',
  'spinner_utility',
  'access_level_tree',
  'all_columns',
  'cycles',
  'profiles',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $stateParams,
    ah_service,
    inventory_service,
    Notification,
    simple_modal_service,
    spinner_utility,
    access_level_tree,
    all_columns,
    cycles,
    profiles
  ) {
    // INIT
    $scope.data = { state: { extra_data: {} } };
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.inventory_types = ['Property', 'TaxLot'];
    const table_name = $scope.inventory_type === 'taxlots' ? 'TaxLotState' : 'PropertyState';
    $scope.cycles = cycles.cycles;
    $scope.profiles = profiles;
    $scope.profile = [];
    $scope.columns = all_columns;
    $scope.form_errors = []

    $scope.matching_columns = [];
    $scope.extra_columns = [];
    $scope.canonical_columns = [];
    $scope.columns.forEach((c) => {
      if (c.table_name === table_name) {
        if (c.is_matching_criteria) $scope.matching_columns.push(c);
        if (c.is_extra_data) $scope.extra_columns.push(c);
        if (!c.is_extra_data && !c.derived_column) $scope.canonical_columns.push(c);
      }
    });
    // create a copy, not a reference. from_column contents is a list of columns dicts
    $scope.form_columns = [...$scope.matching_columns];
    // form_values allows value persistance
    $scope.form_values = [];

    // DATA VALIDATION
    $scope.$watch('data', () => {
      $scope.valid = $scope.data.cycle && $scope.data.access_level_instance && !_.isEqual($scope.data.state, { extra_data: {} });
      check_form_errors();
    }, true);

    $scope.$watch('form_columns', () => {
      check_form_errors();
    }, true);

    const check_form_errors = () => {
      $scope.form_errors = [];
      if (!$scope.data.cycle) $scope.form_errors.push('Cycle is required');
      check_duplicates();
      check_matching_criteria();
    };

    const check_duplicates = () => {
      const display_name_counts = {};
      let has_duplicates = false;
      $scope.form_columns.forEach((col) => {
        display_name_counts[col.displayName] = (display_name_counts[col.displayName] || 0) + 1;
      });
      $scope.form_columns.forEach(col => {
        col.is_duplicate = display_name_counts[col.displayName] > 1;
        if (col.is_duplicate) has_duplicates = true
      });
      has_duplicates && $scope.form_errors.push('Duplicate columns are not allowed');
    };

    const check_matching_criteria = () => {
      const error = !$scope.form_columns.some(c => c.is_matching_criteria && c.value !== undefined)
      if (error) $scope.form_errors.push('At least one matching criteria must have a value');
    }

    // ACCESS LEVEL TREE
    $scope.access_level_tree = access_level_tree.access_level_tree;
    $scope.level_names = access_level_tree.access_level_names.map((level, i) => ({
      index: i,
      name: level
    }));
    const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);
    $scope.change_selected_level_index = () => {
      const new_level_instance_depth = parseInt($scope.data.level_name_index, 10) + 1;
      $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
    };
    $scope.data.level_name_index = $scope.level_names.at(-1).index;
    $scope.change_selected_level_index();
    $scope.data.access_level_instance = $scope.potential_level_instances.at(0).id;

    // COLUMN LIST PROFILES
    $scope.set_columns = (type) => {
      remove_empty_last_column();
      switch (type) {
        case 'canonical':
          $scope.form_columns = Array.from(new Set([...$scope.form_columns, ...$scope.canonical_columns]));
          break;
        case 'extra':
          $scope.form_columns = Array.from(new Set([...$scope.form_columns, ...$scope.extra_columns]));
          break;
        default:
          $scope.form_columns = [...$scope.matching_columns];
          $scope.form_columns = $scope.form_columns.map((c) => ({ ...c, value: 'null', is_duplicate: false }));
          $scope.form_values = [];
      }
    };

    // FORM LOGIC
    $scope.remove_column = (index, column) => {
      $scope.form_columns.splice(index, 1);
      $scope.form_values[index] = null;
      set_column_value(column, null);
      check_form_errors();
    };

    $scope.add_column = () => $scope.form_columns.push({ displayName: '', table_name });

    const remove_empty_last_column = () => {
      if (!_.isEmpty($scope.form_columns) && $scope.form_columns.at(-1).displayName === '') {
        $scope.form_columns.pop();
      }
    };

    $scope.change_profile = () => {
      const profile_column_names = $scope.profile.columns.map((p) => p.column_name);
      $scope.form_columns = $scope.columns.filter((c) => profile_column_names.includes(c.column_name));
    };

    $scope.select_column = (column, index) => {
      // preserve value if column is duplicate
      if ($scope.form_columns.includes(column)) return;
      column.value = $scope.form_values.at(index);
      $scope.form_columns[index] = column;
    };

    $scope.change_column = (displayName, index) => {
      const defaults = {
        table_name,
        is_extra_data: true,
        is_matching_criteria: false,
        data_type: 'string'
      };
      let column = $scope.columns.find((c) => c.displayName === displayName) || { displayName };
      column = { ...defaults, ...column };
      column.value = $scope.form_values.at(index);
      $scope.form_columns[index] = column;
    };

    $scope.change_value = (column, index) => {
      $scope.form_values[index] = column.value;
      set_column_value(column, column.value);
    };

    const set_column_value = (column, value) => {
      const column_name = column.column_name || column.displayName;
      if (!column_name) return;
      const target = column.is_extra_data ? $scope.data.state.extra_data : $scope.data.state;
      target[column_name] = value;
    };

    $scope.save_inventory = () => {
      const type_name = $scope.inventory_type === 'taxlots' ? 'Tax Lot' : 'Property';
      const cycle_name = $scope.cycles.find((c) => c.id === $scope.data.cycle).name;
      const ali_name = $scope.access_level_tree.find((ali) => ali.id === $scope.data.access_level_instance).name;
      const modalOptions = {
        type: 'default',
        okButtonText: 'Confirm',
        headerText: `Create new ${type_name}`,
        bodyText: `Create ${ali_name} ${type_name} in Cycle ${cycle_name}?`
      };
      const successOptions = {
        type: 'default',
        okButtonText: `View ${type_name}`,
        headerText: 'Success',
        bodyText: `Successfully created ${type_name}`
      };
      simple_modal_service.showModal(modalOptions).then(() => {
        spinner_utility.show();
        inventory_service.create_inventory($scope.data, $scope.inventory_type).then((response) => {
          Notification.success(`Successfully created ${type_name}`);
          spinner_utility.hide();
          return response.data.view_id;
        }).then((view_id) => {
          simple_modal_service.showModal(successOptions).then(() => {
            window.location.href = `/app/#/${$scope.inventory_type}/${view_id}`;
          }).catch(() => {
            $state.reload();
          });
        }).catch(() => {
          Notification.error(`Failed to create ${type_name}`);
        });
      });
    };
  }
]);
