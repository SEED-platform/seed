/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.column_mappings', []).controller('column_mappings_controller', [
  '$scope',
  '$state',
  '$log',
  '$uibModal',
  'Notification',
  'auth_payload',
  'column_mapping_profiles_payload',
  'column_mappings_service',
  'inventory_service',
  'mappable_property_columns_payload',
  'mappable_taxlot_columns_payload',
  'organization_payload',
  'urls',
  'COLUMN_MAPPING_PROFILE_TYPE_NORMAL',
  'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT',
  'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $log,
    $uibModal,
    Notification,
    auth_payload,
    column_mapping_profiles_payload,
    column_mappings_service,
    inventory_service,
    mappable_property_columns_payload,
    mappable_taxlot_columns_payload,
    organization_payload,
    urls,
    COLUMN_MAPPING_PROFILE_TYPE_NORMAL,
    COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT,
    COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM
  ) {
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.state = $state.current;

    $scope.mappable_property_columns = mappable_property_columns_payload;
    $scope.mappable_taxlot_columns = mappable_taxlot_columns_payload;

    // Helpers to convert to and from DB column names and column display names
    const mapping_db_to_display = (mapping) => {
      let mappable_column;

      if (mapping.to_table_name === 'PropertyState') {
        mappable_column = _.find($scope.mappable_property_columns, { column_name: mapping.to_field });
      } else if (mapping.to_table_name === 'TaxLotState') {
        mappable_column = _.find($scope.mappable_taxlot_columns, { column_name: mapping.to_field });
      }

      if (mappable_column) {
        mapping.to_field = mappable_column.displayName;
      }
    };

    const mapping_display_to_db = (mapping) => {
      // Also, clear from_units if mapping is not for units col
      if (!$scope.is_area_column(mapping) && !$scope.is_eui_column(mapping) && !$scope.is_ghg_column(mapping) && !$scope.is_ghg_intensity_column(mapping)) {
        mapping.from_units = null;
      }

      let mappable_column;
      if (mapping.to_table_name === 'PropertyState') {
        mappable_column = _.find($scope.mappable_property_columns, { displayName: mapping.to_field });
      } else if (mapping.to_table_name === 'TaxLotState') {
        mappable_column = _.find($scope.mappable_taxlot_columns, { displayName: mapping.to_field });
      }

      if (mappable_column) {
        mapping.to_field = mappable_column.column_name;
      }
    };

    // On page load, convert DB field names to display names
    _.forEach(column_mapping_profiles_payload, (profile) => {
      _.forEach(profile.mappings, mapping_db_to_display);
    });

    $scope.profiles = column_mapping_profiles_payload;

    $scope.current_profile = $scope.profiles[0] ?? {};
    $scope.dropdown_selected_profile = $scope.current_profile;

    // Inventory Types
    $scope.setAllFields = '';
    $scope.setAllFieldsOptions = [
      {
        name: 'Property',
        value: 'PropertyState'
      },
      {
        name: 'Tax Lot',
        value: 'TaxLotState'
      }
    ];

    const analyze_chosen_inventory_types = () => {
      const chosenTypes = _.uniq(_.map($scope.current_profile.mappings, 'to_table_name'));

      if (chosenTypes.length === 1) {
        $scope.setAllFields = _.find($scope.setAllFieldsOptions, { value: chosenTypes[0] });
      } else {
        $scope.setAllFields = '';
      }
    };

    // On load...
    analyze_chosen_inventory_types();

    // change the sorting icon based on the state
    $scope.get_sort_icon = (which) => {
      if (which === $scope.column_sort) {
        if ($scope.column_sort_direction === 'desc') {
          return 'fa-arrow-down-z-a';
        }
        return 'fa-arrow-down-a-z';
      }
      return 'fa-sort text-muted';
    };

    // which columns are sortable and which fields are they sorted on?
    const sort_column_fields = {
      seed: 'to_field',
      file: 'from_field'
    };

    // sorts by a column
    $scope.sort_by = (column) => {
      // initialize column if necessary
      if (!$scope.column_sort) $scope.column_sort = 'seed';

      // determine direction
      if (column !== $scope.column_sort) {
        $scope.column_sort = column;
        $scope.column_sort_direction = 'asc';
      } else {
        $scope.column_sort_direction = $scope.column_sort_direction === 'asc' ? 'desc' : 'asc';
      }

      // sort mappings by the appropriate column, using lower case to fix lodash's method of alphabetical sorting
      $scope.current_profile.mappings = _.sortBy($scope.current_profile.mappings, [(map) => map[sort_column_fields[column]].toLowerCase()]);

      // reverse the sort if descending
      if ($scope.column_sort_direction === 'desc') {
        $scope.current_profile.mappings.reverse();
      }
    };

    // run once to initialize sorting
    $scope.sort_by('seed');

    $scope.updateSingleInventoryTypeDropdown = () => {
      analyze_chosen_inventory_types();

      $scope.flag_change();
    };

    $scope.setAllInventoryTypes = () => {
      _.forEach($scope.current_profile.mappings, (mapping) => {
        if (mapping.to_table_name !== $scope.setAllFields.value) {
          mapping.to_table_name = $scope.setAllFields.value;
          $scope.flag_change();
        }
      });
    };

    // Profile-level CRUD modal-rending actions
    $scope.new_profile = () => {
      const profileData = angular.copy($scope.current_profile);
      // change the profile type to custom if we've edited a default profile
      if ($scope.current_profile.profile_type === COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT) {
        profileData.profile_type = COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM;
      }

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/column_mapping_profile_modal.html`,
        controller: 'column_mapping_profile_modal_controller',
        resolve: {
          action: () => 'new',
          data: () => profileData,
          org_id: () => $scope.org.id
        }
      });

      modalInstance.result.then((new_profile) => {
        $scope.profiles.push(new_profile);
        $scope.current_profile = _.last($scope.profiles);
        $scope.dropdown_selected_profile = $scope.current_profile;

        $scope.changes_possible = false;
        Notification.primary(`Saved ${$scope.current_profile.name}`);
      });
    };

    $scope.rename_profile = () => {
      const old_name = $scope.current_profile.name;

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/column_mapping_profile_modal.html`,
        controller: 'column_mapping_profile_modal_controller',
        resolve: {
          action: () => 'rename',
          data: () => $scope.current_profile,
          org_id: () => $scope.org.id
        }
      });

      modalInstance.result.then((new_name) => {
        const profile_index = _.findIndex($scope.profiles, ['id', $scope.dropdown_selected_profile.id]);
        $scope.profiles[profile_index].name = new_name;

        Notification.primary(`Renamed ${old_name} to ${new_name}`);
      });
    };

    $scope.remove_profile = () => {
      const old_profile = angular.copy($scope.current_profile);

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/column_mapping_profile_modal.html`,
        controller: 'column_mapping_profile_modal_controller',
        resolve: {
          action: () => 'remove',
          data: () => $scope.current_profile,
          org_id: () => $scope.org.id
        }
      });

      modalInstance.result.then(() => {
        _.remove($scope.profiles, old_profile);
        $scope.current_profile = $scope.profiles[0] ?? {};
        $scope.dropdown_selected_profile = $scope.current_profile;
        $scope.changes_possible = false;
      });
    };

    $scope.save_profile = () => {
      // If applicable, convert display names to db names for saving
      _.forEach($scope.current_profile.mappings, mapping_display_to_db);
      const updated_data = { mappings: $scope.current_profile.mappings };

      column_mappings_service.update_column_mapping_profile($scope.org.id, $scope.current_profile.id, updated_data).then((result) => {
        // If applicable, convert db names back to display names for rendering
        _.forEach($scope.current_profile.mappings, mapping_db_to_display);
        $scope.current_profile.updated = result.data.updated;

        const profile_id = $scope.current_profile.id;
        _.find($scope.profiles, ['id', profile_id]).mappings = $scope.current_profile.mappings;

        $scope.changes_possible = false;
        Notification.primary(`Saved ${$scope.current_profile.name}`);
      });
    };

    $scope.export_profile = () => {
      column_mappings_service.export_mapping_profile($scope.org.id, $scope.current_profile.id).then((data) => {
        const blob = new Blob([data], { type: 'text/csv' });
        saveAs(blob, `${$scope.current_profile.name}_mapping_profile.csv`);
        Notification.primary(`Data exported for '${$scope.current_profile.name}'`);
      });
    };

    // Track changes to warn users about losing changes when data could be lost
    $scope.changes_possible = false;

    const get_default_quantity_units = (col) => {
      // TODO - hook up to org preferences / last mapping in DB
      if ($scope.is_eui_column(col)) {
        return 'kBtu/ft**2/year';
      }
      if ($scope.is_area_column(col)) {
        return 'ft**2';
      }
      if ($scope.is_ghg_column(col)) {
        return 'MtCO2e/year';
      }
      if ($scope.is_ghg_intensity_column(col)) {
        return 'MtCO2e/ft**2/year';
      }
      return null;
    };

    $scope.flag_change = (col) => {
      if (col) {
        // Reevaluate units
        col.from_units = get_default_quantity_units(col);
      }

      $scope.changes_possible = true;
    };

    $scope.check_for_changes = () => {
      if ($scope.changes_possible) {
        $uibModal
          .open({
            template:
              '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch profiles without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch Profiles</button></div>'
          })
          .result.then(() => {
            $scope.changes_possible = false;
          })
          .catch(() => {
            $scope.dropdown_selected_profile = $scope.current_profile;
          });
      }

      $scope.current_profile = $scope.dropdown_selected_profile;
      analyze_chosen_inventory_types();
    };

    // Handle units
    const eui_columns = _.filter($scope.mappable_property_columns, { data_type: 'eui' });
    $scope.is_eui_column = (
      mapping // All of these are on the PropertyState table
    ) => mapping.to_table_name === 'PropertyState' && Boolean(_.find(eui_columns, { displayName: mapping.to_field }));

    const area_columns = _.filter($scope.mappable_property_columns, { data_type: 'area' });
    $scope.is_area_column = (
      mapping // All of these are on the PropertyState table
    ) => mapping.to_table_name === 'PropertyState' && Boolean(_.find(area_columns, { displayName: mapping.to_field }));

    const ghg_columns = _.filter($scope.mappable_property_columns, { data_type: 'ghg' });
    $scope.is_ghg_column = (
      mapping // All of these are on the PropertyState table
    ) => mapping.to_table_name === 'PropertyState' && Boolean(_.find(ghg_columns, { displayName: mapping.to_field }));

    const ghg_intensity_columns = _.filter($scope.mappable_property_columns, { data_type: 'ghg_intensity' });
    $scope.is_ghg_intensity_column = (
      mapping // All of these are on the PropertyState table
    ) => mapping.to_table_name === 'PropertyState' && Boolean(_.find(ghg_intensity_columns, { displayName: mapping.to_field }));

    // Add and remove column methods
    $scope.add_new_column = () => {
      const empty_row = {
        from_field: '',
        from_units: null,
        to_field: '',
        to_table_name: ''
      };

      if ($scope.current_profile.mappings[0]) {
        $scope.current_profile.mappings.push(empty_row);
      } else {
        $scope.current_profile.mappings = [empty_row];
      }
      $scope.flag_change();
    };

    $scope.remove_column = (index) => {
      $scope.current_profile.mappings.splice(index, 1);
      $scope.flag_change();
    };

    $scope.remove_all_columns = () => {
      $scope.current_profile.mappings = [];
      $scope.flag_change();
    };

    // Copy Comma-delimited list into headers
    $scope.csv_headers = '';

    $scope.copy_csv_headers = () => {
      $uibModal
        .open({
          template:
            '<div class="modal-header">' +
            '<h3 class="modal-title" translate>Replacing Existing Columns</h3>' +
            '</div>' +
            '<div class="modal-body" translate>This action replaces any of your current columns with the comma-delmited columns you provided. Would you like to continue?</div>' +
            '<div class="modal-footer">' +
            '<button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button>' +
            '<button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Yes</button>' +
            '</div>'
        })
        .result.then(() => {
          $scope.current_profile.mappings = [];
          _.forEach($scope.csv_headers.split(','), (col_header) => {
            $scope.add_new_column();
            _.last($scope.current_profile.mappings).from_field = col_header;
          });
        })
        .catch(() => {});
    };

    // Copy Data File Header values into SEED Header values
    $scope.mirror_data_file_headers = () => {
      _.forEach($scope.current_profile.mappings, (mapping) => {
        mapping.to_field = mapping.from_field;
      });

      $scope.flag_change();
    };

    $scope.suggestions_from_existing_columns = () => {
      const raw_headers = _.map($scope.current_profile.mappings, 'from_field');

      column_mappings_service.get_header_suggestions(raw_headers).then((results) => {
        _.forEach($scope.current_profile.mappings, (mapping) => {
          const [to_table_name, to_field] = results.data[mapping.from_field];
          mapping.to_table_name = to_table_name;
          mapping.to_field = to_field;

          mapping_db_to_display(mapping);
        });
        $scope.flag_change();
      });
    };

    // Identify individual header duplicates and if a profile has header duplicates
    $scope.is_file_header_duplicate = (mapping) => {
      const mapping_by_from_field = _.filter($scope.current_profile.mappings, { from_field: mapping.from_field });
      return mapping_by_from_field.length > 1;
    };

    $scope.header_duplicates_present = () => {
      const grouped_by_from_field = _.groupBy($scope.current_profile.mappings, 'from_field');

      return Boolean(_.find(_.values(grouped_by_from_field), (group) => group.length > 1));
    };

    $scope.empty_units_present = () => Boolean(
      _.find($scope.current_profile.mappings, (field) => {
        const has_units = $scope.is_area_column(field) || $scope.is_eui_column(field) || $scope.is_ghg_column(field) || $scope.is_ghg_intensity_column(field);
        return field.to_table_name === 'PropertyState' && field.from_units === null && has_units;
      })
    );

    $scope.profile_action_ok = (action) => {
      if ($scope.current_profile.profile_type === COLUMN_MAPPING_PROFILE_TYPE_NORMAL) {
        return true;
      }

      if ($scope.current_profile.profile_type === COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT) {
        return false;
      }

      if ($scope.current_profile.profile_type === COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM) {
        const allowed_actions = ['update', 'rename', 'delete', 'change_to_field', 'change_from_units'];
        return allowed_actions.includes(action);
      }

      $log.warn(`Unknown profile type "${$scope.current_profile.profile_type}"`);
      return false;
    };
  }
]);
