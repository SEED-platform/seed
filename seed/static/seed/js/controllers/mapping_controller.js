/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.mapping', [])
  .controller('mapping_controller', [
    '$scope',
    '$log',
    '$q',
    '$filter',
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
    'data_quality_service',
    'inventory_service',
    'geocode_service',
    'organization_service',
    '$translate',
    'i18nService', // from ui-grid
    function (
      $scope,
      $log,
      $q,
      $filter,
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
      data_quality_service,
      inventory_service,
      geocode_service,
      organization_service,
      $translate,
      i18nService
    ) {
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

      $scope.isValidCycle = Boolean(_.find(cycles.cycles, {id: $scope.import_file.cycle}));

      var matching_criteria_columns = [];
      matching_criteria_columns_payload.PropertyState = _.map(matching_criteria_columns_payload.PropertyState, function (column_name) {
        var display_name = _.find($scope.mappable_property_columns, {column_name: column_name}).display_name;
        matching_criteria_columns.push(display_name);
        return {
          column_name: column_name,
          display_name: display_name
        };
      });
      matching_criteria_columns_payload.TaxLotState = _.map(matching_criteria_columns_payload.TaxLotState, function (column_name) {
        var display_name = _.find($scope.mappable_taxlot_columns, {column_name: column_name}).display_name;
        matching_criteria_columns.push(display_name);
        return {
          column_name: column_name,
          display_name: display_name
        };
      });
      $scope.matching_criteria_columns = _.uniq(matching_criteria_columns).sort().join(', ');
      $scope.property_matching_criteria_columns = _.map(matching_criteria_columns_payload.PropertyState, 'display_name').sort().join(', ');
      $scope.taxlot_matching_criteria_columns = _.map(matching_criteria_columns_payload.TaxLotState, 'display_name').sort().join(', ');

      $scope.setAllFields = '';
      $scope.setAllFieldsOptions = [{
        name: 'Property',
        value: 'PropertyState'
      }, {
        name: 'Tax Lot',
        value: 'TaxLotState'
      }];

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
          col.is_duplicate = _.get(suggestions, potential, 0) > 1;
          duplicates_present = duplicates_present || col.is_duplicate;
        });

        $scope.duplicates_present = duplicates_present;
      };

      /**
       * initialize_mappings: prototypical inheritance for all the raw columns
       * called by init()
       */
      var initialize_mappings = function () {
        _.forEach($scope.raw_columns, function (name) {
          var suggestion = $scope.suggested_mappings[name];

          var col = {
            name: name,
            suggestion_column_name: suggestion[1],
            suggestion_table_name: suggestion[0],
            raw_data: _.map(first_five_rows_payload.first_five_rows, name)
          };

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
          } else {
            // No match, generate title-cased name
            col.suggestion = $filter('titleCase')(col.suggestion_column_name);
            col.suggestion_column_name = null;
          }

          col.from_units = get_default_quantity_units(col);

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
      };

      var org_id = user_service.get_organization().id;
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
       * check_fields: called by ng-disabled for "Map Your Data" button.  Checks for duplicates and for required fields.
       */
      $scope.check_fields = function () {
        return $scope.duplicates_present || $scope.empty_fields_present() || !$scope.required_property_fields_present() || !$scope.required_taxlot_fields_present();
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
          data_quality_service.start_data_quality_checks_for_import_file(user_service.get_organization().id, $scope.import_file.id).then(function (response) {
            data_quality_service.data_quality_checks_status(response.progress_key).then(function (check_result) {
              // Fetch data quality check results
              $scope.data_quality_results_ready = false;
              $scope.data_quality_results = data_quality_service.get_data_quality_results(user_service.get_organization().id, check_result.unique_id);
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
            importFileId: function () {
              return $scope.import_file.id;
            },
            orgId: _.constant(user_service.get_organization().id)
          }
        });
      };

      var init = function () {
        initialize_mappings();

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
