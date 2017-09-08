/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.mapping', [])
  .controller('mapping_controller', [
    '$scope',
    '$log',
    '$q',
    'import_file_payload',
    'suggested_mappings_payload',
    'raw_columns_payload',
    'first_five_rows_payload',
    'cycles',
    'mappingValidatorService',
    'mapping_service',
    'spinner_utility',
    'urls',
    '$uibModal',
    'user_service',
    'uploader_service',
    '$http',
    '$filter',
    'data_quality_service',
    'inventory_service',
    'flippers',
    function ($scope,
              $log,
              $q,
              import_file_payload,
              suggested_mappings_payload,
              raw_columns_payload,
              first_five_rows_payload,
              cycles,
              mappingValidatorService,
              mapping_service,
              spinner_utility,
              urls,
              $uibModal,
              user_service,
              uploader_service,
              $http,
              $filter,
              data_quality_service,
              inventory_service,
              flippers) {
      var db_field_columns = suggested_mappings_payload.column_names;
      var columns = suggested_mappings_payload.columns;
      var extra_data_columns = _.filter(columns, 'extra_data');
      var original_columns = _.map(columns, function f (n) {
        return n.name;
      });
      // var original_columns = angular.copy(db_field_columns.concat(extra_data_columns));
      $scope.flippers = flippers; // make available in partials/ng-if

      // Readability for db columns.
      for (var i = 0; i < db_field_columns.length; i++) {
        db_field_columns[i] = $filter('titleCase')(db_field_columns[i]);
      }

      $scope.typeahead_columns = _.uniq(db_field_columns.concat(_.map(extra_data_columns, 'name')));

      if (!flippers.is_active('release:use_pint')) {
        // db may return _pint columns; don't suggest them in the typeahead
        var is_pint_column = function (s) {
          return /\s+Pint$/.test(s);
        };
        _.remove($scope.typeahead_columns, is_pint_column);
      }

      $scope.tabs = {
        one_active: true,
        two_active: false,
        three_active: false
      };

      $scope.import_file = import_file_payload.import_file;
      $scope.import_file.matching_finished = false;
      $scope.suggested_mappings = suggested_mappings_payload.suggested_column_mappings;
      angular.forEach($scope.suggested_mappings, function (v) {
        // only title case fields like address_line_1 which have had their
        // typeahead suggestions title cased
        if (!_.includes($scope.typeahead_columns, v[1])) {
          v[1] = $filter('titleCase')(v[1]);
        }
      });

      $scope.raw_columns = raw_columns_payload.raw_columns;
      $scope.first_five = first_five_rows_payload.first_five_rows;
      $scope.building_column_types = suggested_mappings_payload.columns;
      $scope.validator_service = mappingValidatorService;
      $scope.user = $scope.user || {};
      // Where we store which columns get concatenated and in which order.
      // Keyed on destination mapping name.

      $scope.review_mappings = false;
      $scope.show_mapped_buildings = false;

      $scope.isValidCycle = !!_.find(cycles.cycles, {id: $scope.import_file.cycle});

      /**
       * Gets the row-level validity for a Table Column Mapping.
       *
       * @param tcm: table column mapping object.
       * @param to_validate: array of strings, values from example data.
       */
      // $scope.get_validity = function (tcm) {
      //   /*var diff = tcm.raw_data.length - tcm.invalids.length;
      //    // Used to display the state of the row overall.
      //    if (_.isUndefined(tcm.invalids)) {
      //    return undefined;
      //    }
      //    if ( tcm.invalids.length === 0) {
      //    return 'valid';
      //    }
      //    if (diff > 1) {
      //    return 'semivalid';
      //    }
      //    if (diff < 1) {
      //    return 'invalid';
      //    }*/
      //   return 'valid';
      // };
      $scope.get_validity = _.constant('valid');

      /**
       * set_td_class
       * Gets called on each cell in a table on the mapping page.
       * Return true if a column value is invalid for a TCM.
       */
      $scope.set_td_class = function (tcm, col_value) {
        // If we don't want to map a column, don't validate it.
        tcm = tcm || {};
        if (tcm.suggestion === '') {
          return '';
        }
        for (var i = 0; _.isUndefined(tcm.invalids) && i < tcm.invalids.length; i++) {
          if (col_value === tcm.invalids[i]) {
            if (tcm.validity === 'semivalid') {
              return 'warning';
            }
            return 'danger';
          }
        }
      };

      $scope.setAllFields = '';
      $scope.setAllFieldsOptions = [{
        name: 'Property',
        value: 'PropertyState'
      }, {
        name: 'Tax Lot',
        value: 'TaxLotState'
      }];
      $scope.setAllInventoryTypes = function () {
        _.forEach($scope.valids, function (tcm) {
          if (tcm.suggestion_table_name !== $scope.setAllFields.value) {
            tcm.suggestion_table_name = $scope.setAllFields.value;
            $scope.change(tcm, true);
          }
        });
        $scope.updateColDuplicateStatus();
      };
      $scope.updateInventoryTypeDropdown = function () {
        var chosenTypes = _.uniq(_.map($scope.valids, 'suggestion_table_name'));
        if (chosenTypes.length === 1) $scope.setAllFields = _.find($scope.setAllFieldsOptions, {value: chosenTypes[0]});
        else $scope.setAllFields = '';
      };

      /**
       * Validates example data related to a raw column using a validator service.
       *
       * @param tcm: a table column mapping object.
       * @modifies: attributes on the table column mapping object.
       */
      $scope.validate_data = function (tcm) {
        tcm.user_suggestion = true;
        if (!_.isUndefined(tcm.suggestion) && !_.isEmpty(tcm.suggestion)) {
          var type;

          // find the column in the list of building_columns
          type = _.find($scope.building_column_types, {
            name: angular.lowercase(tcm.suggestion).replace(/ /g, '_')
          });

          // if the suggestion isn't found in the building columns then
          // do we need to do something? Set the unit data type regardless.
          if (_.isUndefined(type)) {
            tcm.suggestion_type = '';
          } else {
            tcm.suggestion_type = type.js_type;
          }

          tcm.invalids = $scope.validator_service.validate(
            tcm.raw_data, type
          );
          tcm.validity = $scope.get_validity(tcm);
        } else {
          tcm.validity = null;
          tcm.invalids = [];
        }
      };

      /**
       * change: called when a user selects a mapping change. `change` should
       * either save the new mapping to the back-end or wait until all mappings
       * are complete.
       *
       * `change` should indicate to the user if a table column is already mapped
       * to another csv raw column header
       *
       * @param tcm: table column mapping object. Represents the database fields <-> raw
       *  relationship.
       */
      $scope.change = function (tcm, checkingMultiple) {
        // Validate that the example data will convert.
        $scope.validate_data(tcm);

        if (!checkingMultiple) $scope.updateColDuplicateStatus();
      };

      $scope.updateColDuplicateStatus = function () {
        // Build suggestions with counts
        var suggestions = {};
        _.forEach($scope.raw_columns, function (col) {
          if (!_.isUndefined(col.suggestion) && !_.isEmpty(col.suggestion) && col.mapped_row) {
            var potential = col.suggestion + '.' + col.suggestion_table_name;
            if (!_.has(suggestions, potential)) suggestions[potential] = 1;
            else suggestions[potential]++;
          }
        });

        // Verify that we don't have any duplicate mappings.
        _.forEach($scope.raw_columns, function (col) {
          var potential = col.suggestion + '.' + col.suggestion_table_name;
          col.is_duplicate = _.get(suggestions, potential, 0) > 1;
        });
      };

      /**
       * update_raw_columns: prototypical inheritance for all the raw columns
       * called by init()
       */
      var update_raw_columns = function () {
        var raw_columns_prototype = {
          building_columns: [''].concat(
            _.uniq(original_columns)
          ),
          suggestion: '',
          user_suggestion: false,
          // Items used to create a concatenated object get set to true
          is_a_concat_parameter: false,
          // Result of a concatenation gets set to true
          is_concatenated: false,
          find_suggested_mapping: function (suggestions) {
            var that = this;
            angular.forEach(suggestions, function (value, key) {
              // Check first element of each value to see if it matches.
              // if it does, then save that key as a suggestion
              if (key === that.name) {
                if (!_.isUndefined(value[0][0]) && angular.isArray(value[0])) {
                  that.suggestion = value[0][0];
                } else {
                  that.suggestion_table_name = value[0];
                  that.suggestion = value[1];
                }
                that.confidence = value[2];
                // if mapping is finished, don't show suggestions
                if ($scope.import_file.matching_done && that.confidence < 100) {
                  that.suggestion = '';
                }
              }
            });
          },
          confidence_text: function () {
            if (this.confidence < 40) {
              return 'low';
            }
            if (this.confidence < 75) {
              return 'med';
            }
            if (this.confidence >= 75) {
              return 'high';
            }
            return '';
          },
          label_status: function () {
            var status;
            var that = this;
            if (!that.mapped_row) {
              status = 'default';
            } else if (that.is_duplicate || that.validity === 'invalid') {
              status = 'danger';
            } else if (that.validity === 'valid') {
              status = 'success';
            } else {
              // that.validity === 'semivalid'
              status = 'warning';
            }
            return status;
          }
        };
        var temp_columns = [];
        var i = 0;
        angular.forEach($scope.raw_columns, function (c) {
          var tcm = {};
          i += 1;
          tcm.name = c;
          tcm.row = i;
          tcm.raw_data = [];
          angular.forEach($scope.first_five, function (value) {
            angular.forEach(value, function (v, k) {
              if (k === tcm.name) {
                tcm.raw_data.push(v);
              }
            });
          });

          angular.extend(tcm, raw_columns_prototype);
          temp_columns.push(tcm);
          tcm.find_suggested_mapping($scope.suggested_mappings);
          tcm.mapped_row = tcm.suggestion !== '';
          $scope.validate_data(tcm); // Validate our system-suggestions.
        });
        // Set the first_five to be an attribute of tcm.
        $scope.raw_columns = temp_columns;
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
            minWidth: 75,
            width: 150
          };
          var existing_property_keys = _.keys(data.properties[0]);
          var existing_extra_property_keys = existing_property_keys.length ? _.keys(data.properties[0].extra_data) : [];
          var existing_taxlot_keys = _.keys(data.tax_lots[0]);
          var existing_extra_taxlot_keys = existing_taxlot_keys.length ? _.keys(data.tax_lots[0].extra_data) : [];
          _.map($scope.property_columns, function (col) {
            var options = {};
            if (!_.includes(existing_property_keys, col.name) && !_.includes(existing_extra_property_keys, col.name)) col.visible = false;
            else {
              if (col.type == 'number') options.filter = inventory_service.numFilter();
              else options.filter = inventory_service.textFilter();
            }
            return _.defaults(col, options, defaults);
          });
          _.map($scope.taxlot_columns, function (col) {
            var options = {};
            if (!_.includes(existing_taxlot_keys, col.name) && !_.includes(existing_extra_taxlot_keys, col.name)) {
              col.visible = false;
            } else {
              if (col.type == 'number') options.filter = inventory_service.numFilter();
              else options.filter = inventory_service.textFilter();
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
          // Fetch data quality check results
          $scope.data_quality_results_ready = false;
          $scope.data_quality_results = data_quality_service.get_data_quality_results($scope.import_file.id);
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
      };

      /**
       * Get_mappings
       * Pull out the mappings of the TCM objects (stored in raw_columns) list
       * into a data structure in the format of
       *      [
       *          {
       *              "from_field": <raw>,
       *              "to_field": <dest>,
       *              "to_table_name": "PropertyState"
       *          },{
       *              ...
       *          }
       */
      $scope.get_mappings = function () {
        var mappings = [];
        for (var i = 0; i < $scope.raw_columns.length; i++) {
          var tcm = $scope.raw_columns[i];
          var header = tcm.name;
          var suggestion;
          // We're not mapping columns that are getting concatenated.
          if (tcm.is_a_concat_parameter) {
            continue;
          }
          // If we have a concatenated column, then we encode the raw_header
          // as the sources.
          if (tcm.is_concatenated) {
            header = tcm.source_headers;
          }
          // don't map ignored rows
          suggestion = tcm.mapped_row ? tcm.suggestion : '';
          mappings.push({
            from_field: header,
            to_field: suggestion,
            to_table_name: tcm.suggestion_table_name
          });
        }
        return mappings;
      };

      // As far as I can tell, this is never used.
      // /**
      //  * show_mapping_progress: shows the progress bar and kicks off the mapping,
      //  *   after saving column mappings
      //  */
      // $scope.show_mapping_progress = function () {
      //   $scope.import_file.progress = 0;
      //   $scope.save_mappings = true;
      //   mapping_service.save_mappings(
      //     $scope.import_file.id,
      //     $scope.get_mappings()
      //   ).then(function (data) {
      //       // start mapping
      //       mapping_service.start_mapping($scope.import_file.id).then(function (data) {
      //         // save maps start mapping data
      //         check_mapping(data.progress_key);
      //       });
      //     });
      // };


      /**
       * reverse titleCase mappings which were titleCase in the suggestion input
       */
      var get_untitle_cased_mappings = function () {
        var mappings = $scope.get_mappings();
        _.forEach(mappings, function (m) {
          // Save the field display name here before changing it in the to_field
          m.to_field_display_name = m.to_field;
          var mapping = m.to_field;
          mapping = angular.lowercase(mapping).replace(/ /g, '_');
          if (_.includes(original_columns, mapping)) {
            m.to_field = mapping;
          }
        });

        return mappings;
      };

      /**
       * remap_buildings: shows the progress bar and kicks off the re-mapping,
       *   after saving column mappings, deletes unmatched buildings
       */
      $scope.remap_buildings = function () {
        $scope.import_file.progress = 0;
        $scope.save_mappings = true;
        $scope.review_mappings = true;
        $scope.raw_columns = $scope.valids.concat($scope.duplicates);
        mapping_service.save_mappings(
          $scope.import_file.id,
          get_untitle_cased_mappings()
        )
          .then(function () {
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
       * check_mapping: mapping progress loop
       */
      var check_mapping = function (progress_key) {
        uploader_service.check_progress_loop(
          progress_key,  // key
          0, //starting prog bar percentage
          1.0,  // progress multiplier
          function () {
            $scope.get_mapped_buildings();
          }, function () {
            // Do nothing
          },
          $scope.import_file  // progress bar obj
        );
      };

      /**
       * duplicates_present: used to disable or enable the 'show & review
       *   mappings' button.
       */
      $scope.duplicates_present = function () {
        return Boolean(_.find($scope.raw_columns, 'is_duplicate'));
      };

      /**
       * empty_fields_present: used to disable or enable the 'show & review
       *   mappings' button.
       */
      $scope.empty_fields_present = function () {
        return Boolean(_.find($scope.raw_columns, {suggestion: ''}));
      };

      /**
       * check_fields: called by ng-disabled for "Map Your Data" button.  Checks for duplicates and for required fields.
       */
      $scope.check_fields = function () {
        return $scope.duplicates_present() || $scope.empty_fields_present() || !$scope.required_fields_present();
      };

      /*
       * required_fields_present: check for presence of at least one field used by SEED to match records
       */
      $scope.required_fields_present = function () {
        var required_fields = [
          {header: 'Jurisdiction Tax Lot Id', inventory_type: 'TaxLotState'},
          {header: 'Pm Property Id', inventory_type: 'PropertyState'},
          {header: 'Custom Id 1', inventory_type: 'PropertyState'},
          {header: 'Custom Id 1', inventory_type: 'TaxLotState'},
          {header: 'Address Line 1', inventory_type: 'PropertyState'},
          {header: 'Address Line 1', inventory_type: 'TaxLotState'}
        ];

        function compare_fields (x, y) {
          return x.header == y.suggestion && x.inventory_type == y.suggestion_table_name;
        }

        return _.intersectionWith(required_fields, $scope.raw_columns, compare_fields).length > 0;
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
            }
          }
        });
      };

      var init = function () {
        update_raw_columns();

        $scope.updateColDuplicateStatus();
        $scope.duplicates = $filter('filter')($scope.raw_columns, {is_duplicate: true});
        $scope.duplicates = $filter('orderBy')($scope.duplicates, 'suggestion', false);
        $scope.valids = $filter('filter')($scope.raw_columns, function (col) {
          return !col.is_duplicate;
        });

        var chosenTypes = _.uniq(_.map($scope.valids, 'suggestion_table_name'));
        if (chosenTypes.length == 1) $scope.setAllFields = _.find($scope.setAllFieldsOptions, {value: chosenTypes[0]});
      };
      init();

      /*
       * open_data_upload_modal: defaults to step 7, which triggers the matching
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

      $scope.MAP_copy = 'A \'check\' indicates you want to map a data field header from your import file to either a standard header from the Building Energy Data Exchange Specification (BEDES) or to a custom header of your choice. Unchecked rows will be ignored for mapping purposes and the data will be imported with the header from your import file.';
      $scope.BEDES_copy = 'A Green check in this column indicates the mapping is done to a standard field in the BEDES specification.';
      $scope.VALIDATE_copy = 'Indicates whether data mapping was successful, if there\'s invalid data in your columns, or a duplicate field header mappings that need to be re-mapped to a unique BEDES/non-BEDES field. ';
    }]);
