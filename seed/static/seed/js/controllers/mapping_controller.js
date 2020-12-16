/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.mapping', [])
  .controller('mapping_controller', [
    '$scope',
    '$state',
    '$log',
    '$q',
    '$filter',
    'column_mapping_profiles_payload',
    'import_file_payload',
    'suggested_mappings_payload',
    'raw_columns_payload',
    'first_five_rows_payload',
    'matching_criteria_columns_payload',
    'cycles',
    'mapping_service',
    'spinner_utility',
    'urls',
    '$uibModal',
    'user_service',
    'uploader_service',
    'column_mappings_service',
    'data_quality_service',
    'inventory_service',
    'geocode_service',
    'organization_service',
    'dataset_service',
    '$translate',
    'i18nService', // from ui-grid
    'simple_modal_service',
    'Notification',
    'organization_payload',
    'naturalSort',
    'COLUMN_MAPPING_PROFILE_TYPE_NORMAL',
    'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT',
    'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM',
    function (
      $scope,
      $state,
      $log,
      $q,
      $filter,
      column_mapping_profiles_payload,
      import_file_payload,
      suggested_mappings_payload,
      raw_columns_payload,
      first_five_rows_payload,
      matching_criteria_columns_payload,
      cycles,
      mapping_service,
      spinner_utility,
      urls,
      $uibModal,
      user_service,
      uploader_service,
      column_mappings_service,
      data_quality_service,
      inventory_service,
      geocode_service,
      organization_service,
      dataset_service,
      $translate,
      i18nService,
      simple_modal_service,
      Notification,
      organization_payload,
      naturalSort,
      COLUMN_MAPPING_PROFILE_TYPE_NORMAL,
      COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT,
      COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM
    ) {
      $scope.profiles = [
        {id: 0, mappings: [], name: '<None selected>'}
      ].concat(column_mapping_profiles_payload);

      $scope.dropdown_selected_profile = $scope.current_profile = $scope.profiles[0] || {};
      $scope.organization = organization_payload.organization;

      // Track changes to help prevent losing changes when data could be lost
      $scope.profile_change_possible = false;

      $scope.flag_profile_change = function () {
        $scope.profile_change_possible = true;
      };

      $scope.flag_mappings_change = function () {
        $scope.mappings_change_possible = true;
      };

      $scope.is_buildingsync_and_profile_not_ok = function () {
        if (!$scope.mappingBuildingSync) {
          return false;
        }
        // BuildingSync requires a saved profile to be applied
        return $scope.current_profile.id === 0
          || $scope.profile_change_possible
          || $scope.mappings_change_possible;
      };

      $scope.apply_profile = function () {
        if ($scope.mappings_change_possible) {
          $uibModal.open({
            template: '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch profiles without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch Profiles</button></div>'
          }).result.then(function () {
            $scope.profile_change_possible = false;
            $scope.mappings_change_possible = false;
            $scope.current_profile = $scope.dropdown_selected_profile;
            $scope.initialize_mappings();
            $scope.updateInventoryTypeDropdown();
            $scope.updateColDuplicateStatus();
          }).catch(function () {
            $scope.dropdown_selected_profile = $scope.current_profile;
            return;
          });
        } else {
          $scope.profile_change_possible = false;
          $scope.current_profile = $scope.dropdown_selected_profile;
          $scope.initialize_mappings();
          $scope.updateInventoryTypeDropdown();
          $scope.updateColDuplicateStatus();
        }
      };

      // Profile-level create and update modal-rending actions
      var profile_mappings_from_working_mappings = function () {
        // for to_field, try DB col name, if not use col display name
        return _.reduce($scope.mappings, function (profile_mapping_data, mapping) {
          var this_mapping = {
            from_field: mapping.name,
            from_units: mapping.from_units,
            to_field: mapping.suggestion_column_name || mapping.suggestion || '',
            to_table_name: mapping.suggestion_table_name
          };
          var isBuildingSyncProfile = $scope.current_profile.profile_type !== undefined
            && [
              COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT,
              COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM
            ].includes($scope.current_profile.profile_type);

          if (isBuildingSyncProfile) {
            this_mapping.from_field_value = mapping.from_field_value;
          }
          profile_mapping_data.push(this_mapping);
          return profile_mapping_data;
        }, []);
      };

      $scope.new_profile = function () {
        var profile_mapping_data = profile_mappings_from_working_mappings();

        var profileType;
        if (!$scope.mappingBuildingSync) {
          profileType = COLUMN_MAPPING_PROFILE_TYPE_NORMAL;
        } else {
          profileType = COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM;

          // make sure the new profile mapping data has the required data
          var currentProfileForBuildingSync =
            $scope.current_profile.profile_type !== undefined
            && [
              COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT,
              COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM
            ].includes($scope.current_profile.profile_type);

          if (!currentProfileForBuildingSync) {
            // we need to add mapping data, from_field_value, using the default mapping
            var defaultProfile = $scope.profiles.find(function (profile) {
              return profile.profile_type === COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT;
            });
            profile_mapping_data = profile_mapping_data.map(function (mapping) {
              // find the corresponding mapping in the default profile
              var defaultMapping = defaultProfile.mappings.find(function (defaultMapping) {
                return defaultMapping.from_field === mapping.from_field;
              });
              return _.merge({}, mapping, {
                from_field_value: defaultMapping.from_field_value
              });
            });
          }
        }

        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/column_mapping_profile_modal.html',
          controller: 'column_mapping_profile_modal_controller',
          resolve: {
            action: _.constant('new'),
            data: _.constant({mappings: profile_mapping_data, profile_type: profileType}),
            org_id: _.constant($scope.organization.id)
          }
        });

        modalInstance.result.then(function (new_profile) {
          $scope.profiles.push(new_profile);
          $scope.dropdown_selected_profile = $scope.current_profile = _.last($scope.profiles);

          $scope.profile_change_possible = false;
          $scope.mappings_change_possible = false;
          Notification.primary('Saved ' + $scope.current_profile.name);
        });
      };

      $scope.save_profile = function () {
        var profile_id = $scope.current_profile.id;
        var profile_index = _.findIndex($scope.profiles, ['id', profile_id]);

        var profile_mapping_data = profile_mappings_from_working_mappings();

        column_mappings_service.update_column_mapping_profile($scope.organization.id, profile_id, {mappings: profile_mapping_data}).then(function (result) {
          $scope.profiles[profile_index].mappings = result.data.mappings;
          $scope.profiles[profile_index].updated = result.data.updated;

          $scope.profile_change_possible = false;
          $scope.mappings_change_possible = false;
          Notification.primary('Saved ' + $scope.current_profile.name);
        });
      };

      // let angular-translate be in charge ... need to feed the language-only part of its $translate setting into
      // ui-grid's i18nService
      var stripRegion = function (languageTag) {
        return _.first(languageTag.split('_'));
      };
      i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

      // if (flippers.is_active('release:orig_columns')) {
      //   var is_archived_pre_pint_column = function (s) {
      //     return /\s+Orig$/.test(s);
      //   };
      //   _.remove($scope.typeahead_columns, is_archived_pre_pint_column);
      // }

      $scope.tabs = {
        one_active: true,
        two_active: false,
        three_active: false
      };

      $scope.import_file = import_file_payload.import_file;
      $scope.import_file.matching_finished = false;
      $scope.suggested_mappings = suggested_mappings_payload.suggested_column_mappings;

      $scope.raw_columns = raw_columns_payload.raw_columns;
      $scope.mappable_property_columns = suggested_mappings_payload.property_columns;
      $scope.mappable_taxlot_columns = suggested_mappings_payload.taxlot_columns;
      $scope.mappings = [];

      $scope.review_mappings = false;
      $scope.show_mapped_buildings = false;

      var validCycle = _.find(cycles.cycles, {id: $scope.import_file.cycle});
      $scope.isValidCycle = Boolean(validCycle);
      $scope.cycleName = validCycle.name;

      $scope.mappingBuildingSync = $scope.import_file.source_type === 'BuildingSync Raw';

      matching_criteria_columns_payload.PropertyState = _.map(matching_criteria_columns_payload.PropertyState, function (column_name) {
        var display_name = _.find($scope.mappable_property_columns, {column_name: column_name}).display_name;
        return {
          column_name: column_name,
          display_name: display_name
        };
      });
      matching_criteria_columns_payload.TaxLotState = _.map(matching_criteria_columns_payload.TaxLotState, function (column_name) {
        var display_name = _.find($scope.mappable_taxlot_columns, {column_name: column_name}).display_name;
        return {
          column_name: column_name,
          display_name: display_name
        };
      });

      $scope.property_matching_criteria_columns = _.map(matching_criteria_columns_payload.PropertyState, 'display_name').sort().join(', ');
      $scope.taxlot_matching_criteria_columns = _.map(matching_criteria_columns_payload.TaxLotState, 'display_name').sort().join(', ');

      $scope.setAllFields = '';
      $scope.setAllFieldsOptions = [{
        name: 'Property',
        value: 'PropertyState'
      }];
      if (!$scope.mappingBuildingSync) {
        $scope.setAllFieldsOptions.push({
          name: 'Tax Lot',
          value: 'TaxLotState'
        });
      }

      var eui_columns = _.filter($scope.mappable_property_columns, {data_type: 'eui'});
      $scope.is_eui_column = function (col) {
        // All of these are on the PropertyState table
        return col.suggestion_table_name === 'PropertyState' && Boolean(_.find(eui_columns, {column_name: col.suggestion_column_name}));
      };

      var area_columns = _.filter($scope.mappable_property_columns, {data_type: 'area'});
      $scope.is_area_column = function (col) {
        // All of these are on the PropertyState table
        return col.suggestion_table_name === 'PropertyState' && Boolean(_.find(area_columns, {column_name: col.suggestion_column_name}));
      };

      var get_default_quantity_units = function (col) {
        // TODO - hook up to org preferences / last mapping in DB
        if ($scope.is_eui_column(col)) {
          return 'kBtu/ft**2/year';
        } else if ($scope.is_area_column(col)) {
          return 'ft**2';
        }
        return null;
      };

      $scope.setAllInventoryTypes = function () {
        _.forEach($scope.mappings, function (col) {
          if (col.suggestion_table_name !== $scope.setAllFields.value) {
            col.suggestion_table_name = $scope.setAllFields.value;
            $scope.change(col, true);
          }
        });
        $scope.updateColDuplicateStatus();
      };
      $scope.updateInventoryTypeDropdown = function () {
        var chosenTypes = _.uniq(_.map($scope.mappings, 'suggestion_table_name'));
        if (chosenTypes.length === 1) $scope.setAllFields = _.find($scope.setAllFieldsOptions, {value: chosenTypes[0]});
        else $scope.setAllFields = '';
      };

      /**
       * change: called when a user selects a mapping change. `change` should
       * either save the new mapping to the back-end or wait until all mappings
       * are complete.
       *
       * `change` should indicate to the user if a table column is already mapped
       * to another csv raw column header
       *
       * @param col: table column mapping object. Represents the database fields <-> raw
       *  relationship.
       */
      $scope.change = function (col, checkingMultiple) {
        // Validate that the example data will convert.
        if (!_.isEmpty(col.suggestion)) {
          var match;
          if (col.suggestion_table_name === 'PropertyState') {
            match = _.find($scope.mappable_property_columns, {
              display_name: col.suggestion,
              table_name: 'PropertyState'
            });
          } else {
            match = _.find($scope.mappable_taxlot_columns, {
              display_name: col.suggestion,
              table_name: 'TaxLotState'
            });
          }
          if (match) {
            col.suggestion_column_name = match.column_name;
          } else {
            col.suggestion_column_name = null;
          }
        } else {
          col.suggestion_column_name = null;
        }

        col.from_units = get_default_quantity_units(col);

        $scope.flag_mappings_change();

        if (!checkingMultiple) $scope.updateColDuplicateStatus();
      };

      $scope.updateColDuplicateStatus = function () {
        // Build suggestions with counts
        var suggestions = {};
        _.forEach($scope.mappings, function (col) {
          if (!_.isEmpty(col.suggestion)) {
            var potential = col.suggestion + '.' + col.suggestion_table_name;
            if (!_.has(suggestions, potential)) suggestions[potential] = 1;
            else suggestions[potential]++;
          }
        });

        // Verify that we don't have any duplicate mappings.
        var duplicates_present = false;
        _.forEach($scope.mappings, function (col) {
          var potential = col.suggestion + '.' + col.suggestion_table_name;
          var dup_suggestion = _.get(suggestions, potential, 0) > 1;

          var dup_header = _.filter($scope.raw_columns, function (filter_col) {
            return filter_col === col.name;
          }).length > 1;

          col.is_duplicate = dup_header || dup_suggestion;
          duplicates_present = duplicates_present || col.is_duplicate;
        });

        $scope.duplicates_present = duplicates_present;
      };

      var get_col_from_suggestion = function (name) {

        var suggestion = _.find($scope.current_profile.mappings, {from_field: name}) || {};

        return {
          from_units: suggestion.from_units,
          name: name,
          from_field_value: suggestion.from_field_value,
          raw_data: _.map(first_five_rows_payload.first_five_rows, name),
          suggestion: suggestion.to_field,
          suggestion_column_name: suggestion.to_field,
          suggestion_table_name: suggestion.to_table_name
        };
      };

      /**
       * initialize_mappings: prototypical inheritance for all the raw columns
       * called by init()
       */
      $scope.initialize_mappings = function () {
        $scope.mappings = [];
        _.forEach($scope.raw_columns, function (name) {
          var col = get_col_from_suggestion(name);
          var match;
          if (col.suggestion_table_name === 'PropertyState') {
            match = _.find($scope.mappable_property_columns, {
              column_name: col.suggestion_column_name,
              table_name: 'PropertyState'
            });
          } else {
            match = _.find($scope.mappable_taxlot_columns, {
              column_name: col.suggestion_column_name,
              table_name: 'TaxLotState'
            });
          }
          if (match) {
            col.suggestion = match.display_name;
          } else if ($scope.mappingBuildingSync) {
            col.suggestion = $filter('titleCase')(col.suggestion_column_name);
          }

          $scope.mappings.push(col);
        });
      };
      /**
       * reset_mappings
       * Ignore suggestions and set all seed data headers to the headers from the original import file on PropertyState
       */
      $scope.reset_mappings = function () {
        _.forEach($scope.mappings, function (col) {
          var changed = false;
          if (col.suggestion !== col.name) {
            col.suggestion = col.name;
            changed = true;
          }
          if (col.suggestion_table_name !== 'PropertyState') {
            col.suggestion_table_name = 'PropertyState';
            changed = true;
          }
          $scope.setAllFields = $scope.setAllFieldsOptions[0];
          if (changed) $scope.change(col, true);
        });
        $scope.updateColDuplicateStatus();
      };

      /**
       * check_reset_mappings
       * Return true if the mappings match the original import file
       */
      $scope.check_reset_mappings = function () {
        return _.every($scope.mappings, function (col) {
          return _.isMatch(col, {
            suggestion: col.name,
            suggestion_table_name: 'PropertyState'
          });
        });
      };

      /**
       * Get_mappings
       * Pull out the mappings of the TCM objects (stored in mappings) list
       * into a data structure in the format of
       *      [
       *          {
       *              "from_field": <raw>,
       *              "from_units": <pint string>,
       *              "to_field": <dest>,
       *              "to_table_name": "PropertyState"
       *          },{
       *              ...
       *          }
       */
      $scope.get_mappings = function () {
        var mappings = [];
        _.forEach($scope.mappings, function (col) {
          mappings.push({
            from_field: col.name,
            from_units: col.from_units || null,
            to_field: col.suggestion_column_name || col.suggestion,
            to_field_display_name: col.suggestion,
            to_table_name: col.suggestion_table_name
          });
        });
        return mappings;
      };

      var get_geocoding_columns = function () {
        geocode_service.check_org_has_geocoding_enabled(org_id).then(function (result) {
          if (result === true) {
            organization_service.geocoding_columns(org_id).then(function (geocoding_columns) {
              $scope.property_geocoding_columns_array = _.map(geocoding_columns.PropertyState, function (column_name) {
                return _.find($scope.mappable_property_columns, {column_name: column_name}).display_name;
              });
              $scope.property_geocoding_columns = $scope.property_geocoding_columns_array.join(', ');

              $scope.taxlot_geocoding_columns_array = _.map(geocoding_columns.TaxLotState, function (column_name) {
                return _.find($scope.mappable_taxlot_columns, {column_name: column_name}).display_name;
              });
              $scope.taxlot_geocoding_columns = $scope.taxlot_geocoding_columns_array.join(', ');
            });
          }
        });
      };

      var org_id = $scope.organization.id;
      geocode_service.check_org_has_api_key(org_id).then(function (result) {
        $scope.org_has_api_key = result;
        if (result) {
          get_geocoding_columns();
        }
      });

      var suggested_address_fields = [
        {column_name: 'address_line_1'},
        {column_name: 'city'},
        {column_name: 'state'},
        {column_name: 'postal_code'}
      ];

      $scope.suggested_fields_present = function () {
        if (!$scope.mappings) return true;

        var intersections = _.intersectionWith(suggested_address_fields, $scope.mappings, function (required_field, raw_col) {
          return required_field.column_name === raw_col.suggestion_column_name;
        }).length;

        return intersections === 4;
      };

      var required_property_fields = [];
      _.forEach(matching_criteria_columns_payload.PropertyState, function (column) {
        required_property_fields.push({column_name: column.column_name, inventory_type: 'PropertyState'});
      });
      /*
       * required_property_fields_present: check for presence of at least one Property field used by SEED to match records
       */
      $scope.required_property_fields_present = function () {
        var property_mappings_found = _.find($scope.mappings, {suggestion_table_name: 'PropertyState'});
        if (!property_mappings_found) return true;

        var intersections = _.intersectionWith(required_property_fields, $scope.mappings, function (required_field, raw_col) {
          return _.isMatch(required_field, {
            column_name: raw_col.suggestion_column_name,
            inventory_type: raw_col.suggestion_table_name
          });
        }).length;

        return intersections > 0;
      };

      var required_taxlot_fields = [];
      _.forEach(matching_criteria_columns_payload.TaxLotState, function (column) {
        required_taxlot_fields.push({column_name: column.column_name, inventory_type: 'TaxLotState'});
      });
      /*
       * required_taxlot_fields_present: check for presence of at least one Tax Lot field used by SEED to match records
       */
      $scope.required_taxlot_fields_present = function () {
        var taxlot_mappings_found = _.find($scope.mappings, {suggestion_table_name: 'TaxLotState'});
        if (!taxlot_mappings_found) return true;

        var intersections = _.intersectionWith(required_taxlot_fields, $scope.mappings, function (required_field, raw_col) {
          return _.isMatch(required_field, {
            column_name: raw_col.suggestion_column_name,
            inventory_type: raw_col.suggestion_table_name
          });
        }).length;

        return intersections > 0;
      };

      /**
       * empty_fields_present: used to disable or enable the 'show & review
       *   mappings' button.
       */
      $scope.empty_fields_present = function () {
        return Boolean(_.find($scope.mappings, {suggestion: ''}));
      };

      /**
       * empty_units_present: used to disable or enable the 'Map Your Data' button if any units are empty
       */
      $scope.empty_units_present = function () {
        return Boolean(_.find($scope.mappings, function (field) {
          return field.suggestion_table_name === 'PropertyState' && field.from_units === null && ($scope.is_area_column(field) || $scope.is_eui_column(field));
        }));
      }

      /**
       * empty_fields_present: used to disable or enable the 'show & review
       *   mappings' button. No warning associated as users "aren't done" listing their mapping settings.
       */
      var suggestions_not_provided_yet = function () {
        var no_suggestion_value = Boolean(_.find($scope.mappings, {suggestion: undefined}));
        var no_suggestion_table_name = Boolean(_.find($scope.mappings, {suggestion_table_name: undefined}));
        return no_suggestion_value || no_suggestion_table_name;
      };

      /**
       * check_fields: called by ng-disabled for "Map Your Data" button.  Checks for duplicates and for required fields.
       */
      $scope.check_fields = function () {
        return $scope.duplicates_present ||
          $scope.empty_fields_present() ||
          $scope.empty_units_present() ||
          !$scope.required_property_fields_present() ||
          !$scope.required_taxlot_fields_present() ||
          suggestions_not_provided_yet();
      };

      /**
       * check_mapping: mapping progress loop
       */
      var check_mapping = function (progress_key) {
        uploader_service.check_progress_loop(
          progress_key, // key
          0, //starting prog bar percentage
          1.0, // progress multiplier
          function () {
            $scope.get_mapped_buildings();
          }, function () {
            // Do nothing
          },
          $scope.import_file // progress bar obj
        );
      };

      /**
       * remap_buildings: shows the progress bar and kicks off the re-mapping,
       *   after saving column mappings, deletes unmatched buildings
       */
      $scope.remap_buildings = function () {
        $scope.import_file.progress = 0;
        $scope.save_mappings = true;
        $scope.review_mappings = true;
        mapping_service.save_mappings(
          $scope.import_file.id,
          $scope.get_mappings()
        ).then(function () {
          // start re-mapping
          mapping_service.remap_buildings($scope.import_file.id).then(function (data) {
            if (data.status === 'error' || data.status === 'warning') {
              $scope.$emit('app_error', data);
              $scope.get_mapped_buildings();
            } else {
              // save maps start mapping data
              check_mapping(data.progress_key);
            }
          });
        });
      };

      /**
       * get_mapped_buildings: gets mapped buildings for the preview table
       */
      $scope.get_mapped_buildings = function () {
        $scope.import_file.progress = 0;
        $scope.save_mappings = true;
        $scope.review_mappings = true;
        $scope.tabs.one_active = false;
        $scope.tabs.two_active = true;

        $scope.save_mappings = false;

        // Request the columns again because they may (most likely)
        // have changed from the initial import
        $q.all([
          inventory_service.get_property_columns(),
          inventory_service.get_taxlot_columns(),
          inventory_service.search_matching_inventory($scope.import_file.id)
        ]).then(function (results) {
          $scope.property_columns = results[0];
          $scope.taxlot_columns = results[1];
          $scope.mappedData = results[2];

          var data = $scope.mappedData;

          var gridOptions = {
            enableFiltering: true,
            enableGridMenu: false,
            enableSorting: true,
            fastWatch: true,
            flatEntityAccess: true
          };

          var defaults = {
            enableHiding: false,
            headerCellFilter: 'translate',
            minWidth: 75,
            width: 150
          };
          var existing_property_keys = _.keys(data.properties[0]);
          var existing_extra_property_keys = existing_property_keys.length ? _.keys(data.properties[0].extra_data) : [];
          var existing_taxlot_keys = _.keys(data.tax_lots[0]);
          var existing_extra_taxlot_keys = existing_taxlot_keys.length ? _.keys(data.tax_lots[0].extra_data) : [];
          _.map($scope.property_columns, function (col) {
            var options = {};
            if (!_.includes(existing_property_keys, col.name) && !_.includes(existing_extra_property_keys, col.name)) {
              col.visible = false;
            } else {
              if (col.data_type === 'datetime') {
                options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
                options.filter = inventory_service.dateFilter();
              } else if (col.data_type === 'area' || col.data_type === 'eui') {
                options.cellFilter = 'number: ' + $scope.organization.display_significant_figures
                options.sortingAlgorithm = naturalSort;
              } else {
                options.filter = inventory_service.combinedFilter();
              }
            }
            return _.defaults(col, options, defaults);
          });
          _.map($scope.taxlot_columns, function (col) {
            var options = {};
            if (!_.includes(existing_taxlot_keys, col.name) && !_.includes(existing_extra_taxlot_keys, col.name)) {
              col.visible = false;
            } else {
              if (col.data_type === 'datetime') {
                options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
                options.filter = inventory_service.dateFilter();
              } else {
                options.filter = inventory_service.combinedFilter();
              }
            }
            return _.defaults(col, options, defaults);
          });

          $scope.propertiesGridOptions = angular.copy(gridOptions);
          $scope.propertiesGridOptions.data = _.map(data.properties, function (prop) {
            return _.defaults(prop, prop.extra_data);
          });
          $scope.propertiesGridOptions.columnDefs = $scope.property_columns;
          $scope.taxlotsGridOptions = angular.copy(gridOptions);
          $scope.taxlotsGridOptions.data = _.map(data.tax_lots, function (taxlot) {
            return _.defaults(taxlot, taxlot.extra_data);
          });
          $scope.taxlotsGridOptions.columnDefs = $scope.taxlot_columns;

          $scope.show_mapped_buildings = true;
        }).catch(function (response) {
          $log.error(response);
        }).finally(function () {
          // Submit the data quality checks and wait for the results
          data_quality_service.start_data_quality_checks_for_import_file($scope.organization.id, $scope.import_file.id).then(function (response) {
            data_quality_service.data_quality_checks_status(response.progress_key).then(function (check_result) {
              // Fetch data quality check results
              $scope.data_quality_results_ready = false;
              $scope.data_quality_results = data_quality_service.get_data_quality_results($scope.organization.id, check_result.unique_id);
              $scope.data_quality_results.then(function (data) {
                $scope.data_quality_results_ready = true;
                $scope.data_quality_errors = 0;
                $scope.data_quality_warnings = 0;
                _.forEach(data, function (datum) {
                  _.forEach(datum.data_quality_results, function (result) {
                    if (result.severity === 'error') $scope.data_quality_errors++;
                    else if (result.severity === 'warning') $scope.data_quality_warnings++;
                  });
                });
              });
            });
          });
        });
      };

      $scope.backToMapping = function () {
        $scope.review_mappings = false;
        $scope.show_mapped_buildings = false;
      };

      /**
       * open_data_quality_modal: modal to present data data_quality warnings and errors
       */
      $scope.open_data_quality_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/data_quality_modal.html',
          controller: 'data_quality_modal_controller',
          size: 'lg',
          resolve: {
            dataQualityResults: function () {
              return $scope.data_quality_results;
            },
            name: function () {
              return $scope.import_file.uploaded_filename;
            },
            uploaded: function () {
              return $scope.import_file.created;
            },
            run_id: function () {
              return $scope.import_file.id;
            },
            orgId: _.constant($scope.organization.id)
          }
        });
      };

      var display_cached_column_mappings = function () {
        var cached_mappings = JSON.parse($scope.import_file.cached_mapped_columns);
        _.forEach($scope.mappings, function (col) {
          var cached_col = _.find(cached_mappings, {from_field: col.name});
          col.suggestion_column_name = cached_col.to_field;
          col.suggestion_table_name = cached_col.to_table_name;
          col.from_units = cached_col.from_units;

          // If available, use display_name, else use raw field name.
          var mappable_column = _.find(
            $scope.mappable_property_columns.concat($scope.mappable_taxlot_columns),
            {column_name: cached_col.to_field, table_name: cached_col.to_table_name}
          );
          if (mappable_column) {
            col.suggestion = mappable_column.display_name;
          } else {
            col.suggestion = cached_col.to_field;
          }
        });
      };

      // If the imported file has generated headers, warn the user and give the
      // option to delete the file
      if ($scope.import_file.has_generated_headers && !$scope.import_file.matching_done) {
        var modalOptions = {
          type: 'default',
          okButtonText: 'Continue',
          cancelButtonText: 'Delete File',
          headerText: 'Missing Headers',
          bodyText: 'This file was missing one or more headers which have been replaced with auto-generated names. This will not affect your data import. If you prefer to use your own headers please select "Delete File", fix the headers and re-upload the file.'
        };
        simple_modal_service.showModal(modalOptions).then(function () {
          // user chose to NOT delete file
        }, function () {
          // user chose to delete file
          dataset_service.delete_file($scope.import_file.id).then(function() {
            Notification.primary('File deleted')
            $state.go('dataset_list');
          }, function(message) {
            $log.error('Error deleting file.', message);
            $state.go('dataset_list');
          })
        });
      }

      var init = function () {
        $scope.initialize_mappings();

        if ($scope.import_file.matching_done) {
          display_cached_column_mappings();
        }

        $scope.updateColDuplicateStatus();
        $scope.updateInventoryTypeDropdown();
      };
      init();

      /*
       * open_data_upload_modal: Save Mappings -- defaults to step 7, which triggers the matching
       *  process and allows the user to add more data if no matches are
       *  available
       *
       * @param {object} dataset: an the import_file's dataset. Used in the
       *   modal to display the file name and match buildings that were created
       *   from the file.
       */
      $scope.open_data_upload_modal = function (dataset) {
        var step = 11;
        var ds = angular.copy(dataset);
        ds.filename = $scope.import_file.uploaded_filename;
        ds.import_file_id = $scope.import_file.id;
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/data_upload_modal.html',
          controller: 'data_upload_modal_controller',
          resolve: {
            cycles: cycles,
            step: function () {
              return step;
            },
            dataset: function () {
              return ds;
            },
            organization: function () {
              return $scope.menu.user.organization;
            }
          }
        });
      };
    }]);
