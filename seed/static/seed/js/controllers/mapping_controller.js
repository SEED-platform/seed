/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.mapping', [])
  .controller('mapping_controller', [
    '$scope',
    'import_file_payload',
    'suggested_mappings_payload',
    'raw_columns_payload',
    'first_five_rows_payload',
    'property_columns',
    'taxlot_columns',
    'cycles',
    'mappingValidatorService',
    'mapping_service',
    'search_service',
    'spinner_utility',
    'urls',
    '$uibModal',
    'user_service',
    'uploader_service',
    '$http',
    '$filter',
    'cleansing_service',
    'inventory_service',
    function ($scope,
              import_file_payload,
              suggested_mappings_payload,
              raw_columns_payload,
              first_five_rows_payload,
              property_columns,
              taxlot_columns,
              cycles,
              mappingValidatorService,
              mapping_service,
              search_service,
              spinner_utility,
              urls,
              $uibModal,
              user_service,
              uploader_service,
              $http,
              $filter,
              cleansing_service,
              inventory_service) {
      var db_field_columns = suggested_mappings_payload.column_names;
      var columns = suggested_mappings_payload.columns;
      var extra_data_columns = _.filter(columns, 'extra_data');
      var original_columns = _.map(columns, function f(n) {
        return n['name']
      });
      // var original_columns = angular.copy(db_field_columns.concat(extra_data_columns));

      // Readability for db columns.
      for (var i = 0; i < db_field_columns.length; i++) {
        db_field_columns[i] = $filter('titleCase')(db_field_columns[i]);
      }

      $scope.typeahead_columns = _.uniq(db_field_columns.concat(_.map(extra_data_columns, 'name')));
      $scope.tabs = {
        one_active: true,
        two_active: false,
        three_active: false
      };

      $scope.import_file = import_file_payload.import_file;
      $scope.import_file.matching_finished = false;
      $scope.suggested_mappings = suggested_mappings_payload.suggested_column_mappings;
      angular.forEach($scope.suggested_mappings, function (v, k) {
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

      $scope.search = angular.copy(search_service);
      $scope.search.has_checkbox = false;
      $scope.search.update_results();

      $scope.isValidCycle = !!_.find(cycles.cycles, {id: $scope.import_file.cycle});

      /*
       * Opens modal for making changes to concatenation changes.
       * NL 2016-11-11: hasn't this been deprecated? Backend doesn't have this anymore.
       */
      $scope.open_concat_modal = function (building_column_types, raw_columns) {
        var concatModalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/concat_modal.html',
          controller: 'concat_modal_controller',
          resolve: {
            building_column_types: function () {
              return Object.keys(building_column_types);
            },
            raw_columns: function () {
              return raw_columns;
            }
          }
        });
      };

      /*
       * Gets the row-level validity for a Table Column Mapping.
       *
       * @param tcm: table column mapping object.
       * @param to_validate: array of strings, values from example data.
       */
      $scope.get_validity = function (tcm) {
        /*var diff = tcm.raw_data.length - tcm.invalids.length;
         // Used to display the state of the row overall.
         if (_.isUndefined(tcm.invalids)) {
         return undefined;
         }
         if ( tcm.invalids.length === 0) {
         return 'valid';
         }
         if (diff > 1) {
         return 'semivalid';
         }
         if (diff < 1) {
         return 'invalid';
         }*/
        return 'valid';
      };

      /*
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
        for (
          var i = 0; _.isUndefined(tcm.invalids) &&
        i < tcm.invalids.length; i++
        ) {
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
        _.forEach($scope.valids, function (valid) {
          valid.suggestion_table_name = $scope.setAllFields.value;
          $scope.change(valid);
          // Check if the mapping button should be disabled.
          $scope.check_fields();
        });
      };
      $scope.setInventoryType = function (tcm) {
        var chosenTypes = _.uniq(_.map($scope.valids, 'suggestion_table_name'));
        if (chosenTypes.length == 1) $scope.setAllFields = _.find($scope.setAllFieldsOptions, {value: chosenTypes[0]});
        else $scope.setAllFields = '';
      };

      $scope.find_duplicates = function (array, element) {
        var indices = [];
        var idx = array.indexOf(element);
        while (idx !== -1) {
          indices.push(idx);
          idx = array.indexOf(element, idx + 1);
        }
        return indices;
      };

      /*
       * Returns true if a TCM row is duplicated elsewhere.
       */
      $scope.is_tcm_duplicate = function (tcm) {
        var suggestions = [];
        for (var i = 0; i < $scope.raw_columns.length; i++) {

          var potential = $scope.raw_columns[i].suggestion + '.' + $scope.raw_columns[i].suggestion_table_name;
          if (_.isUndefined(potential) || _.isEmpty(potential) || !$scope.raw_columns[i].mapped_row) {
            continue;
          }
          suggestions.push(potential);
        }
        var dups = $scope.find_duplicates(suggestions, tcm.suggestion + '.' + tcm.suggestion_table_name);
        return dups.length > 1;
      };

      /*
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
          type = _.find($scope.building_column_types, {'name': angular.lowercase(tcm.suggestion).replace(/ /g, '_')});

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

      /*
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
      $scope.change = function (tcm) {
        // Validate that the example data will convert.
        $scope.validate_data(tcm);
        // Verify that we don't have any duplicate mappings.
        for (var i = 0; i < $scope.raw_columns.length; i++) {
          var inner_tcm = $scope.raw_columns[i];
          inner_tcm.is_duplicate = $scope.is_tcm_duplicate(inner_tcm);
        }
      };

      /*
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
            }
            else if (that.is_duplicate || that.validity === 'invalid') {
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
          angular.forEach($scope.first_five, function (value, key) {
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

      /*
       * get_mapped_buildings: gets mapped buildings for the preview table
       */
      $scope.get_mapped_buildings = function () {
        $scope.import_file.progress = 0;
        $scope.save_mappings = true;
        $scope.review_mappings = true;
        $scope.tabs.one_active = false;
        $scope.tabs.two_active = true;

        $scope.save_mappings = false;

        inventory_service.search_matching_inventory($scope.import_file.id).then(function (data) {
          $scope.mappedData = data;

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
          _.map(property_columns, function (col) {
            var options = {};
            if (!_.includes(existing_property_keys, col.name) && !_.includes(existing_extra_property_keys, col.name)) col.visible = false;
            else {
              if (col.type == 'number') options.filter = inventory_service.numFilter();
              else options.filter = inventory_service.textFilter();
            }
            return _.defaults(col, options, defaults);
          });
          _.forEach(existing_extra_property_keys, function (name) {
            if (!_.find(property_columns, {name: name})) {
              property_columns.push(_.defaults({
                name: name,
                displayName: _.startCase(_.toLower(name)),
                filter: inventory_service.textFilter(),
                related: false
              }, defaults));
            }
          });
          _.map(taxlot_columns, function (col) {
            var options = {};
            if (!_.includes(existing_taxlot_keys, col.name) && !_.includes(existing_extra_taxlot_keys, col.name)) col.visible = false;
            else {
              if (col.type == 'number') options.filter = inventory_service.numFilter();
              else options.filter = inventory_service.textFilter();
            }
            return _.defaults(col, options, defaults);
          });
          _.forEach(existing_extra_taxlot_keys, function (name) {
            if (!_.find(taxlot_columns, {name: name})) {
              taxlot_columns.push(_.defaults({
                name: name,
                displayName: _.startCase(_.toLower(name)),
                filter: inventory_service.textFilter(),
                related: false
              }, defaults));
            }
          });

          $scope.propertiesGridOptions = angular.copy(gridOptions);
          $scope.propertiesGridOptions.data = _.map(data.properties, function (prop) {
            return _.defaults(prop, prop.extra_data);
          });
          $scope.propertiesGridOptions.columnDefs = property_columns;
          $scope.taxlotsGridOptions = angular.copy(gridOptions);
          $scope.taxlotsGridOptions.data = _.map(data.tax_lots, function (taxlot) {
            return _.defaults(taxlot, taxlot.extra_data);
          });
          $scope.taxlotsGridOptions.columnDefs = taxlot_columns;

          $scope.show_mapped_buildings = true;
        }).catch(function (response) {
          console.error(response);
        });
      };

      /*
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
          mappings.push(
            {
              "from_field": header,
              "to_field": suggestion,
              "to_table_name": tcm.suggestion_table_name
            }
          );
        }
        return mappings;
      };

      // As far as I can tell, this is never used.
      // /*
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
          m['to_field_display_name'] = m["to_field"];
          var mapping = m["to_field"];
          mapping = angular.lowercase(mapping).replace(/ /g, '_');
          if (_.includes(original_columns, mapping)) {
            m["to_field"] = mapping;
          }
        });

        return mappings;
      };

      /*
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
          .then(function (data) {
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
          function (data) {  //success fn
            $scope.get_mapped_buildings();
          }, function (data) {  //failure fn
            // Do nothing
          },
          $scope.import_file  // progress bar obj
        );
      };

      /*
       * monitor_typeahead_list: decide if duplicate checking is required in
       * order to enable or disable map data button
       */
      $scope.monitor_typeahead_list = function () {
        var dropdown = angular.element('.uib-dropdown-menu.ng-scope');

        //if dropdown menu is not shown - i.e., the user has typed
        //a new field name and a duplicate field is encountered in the
        //header fields list do a dups check. otherwise disable the button
        if ($scope.duplicates.length > 0) {
          for (var i = 0; i < $scope.duplicates.length; i++) {
            if ($scope.duplicates[i].is_duplicate) {
              return true;
            }
          }
        }
        else {
          if (dropdown.length === 0 || dropdown.css('display') === 'none') {
            var input_focus = $(document.activeElement);

            $('.header-field').each(function () {

              if (!$(this).is(input_focus) && $(this).val() === input_focus.val()) {
                return $scope.duplicates_present();
              }
            });
          }

          else return true;
        }
      };

      /*
       * duplicates_present: used to disable or enable the 'show & review
       *   mappings' button.
       */
      $scope.duplicates_present = function () {
        for (var i = 0; i < $scope.raw_columns.length; i++) {
          var tcm = $scope.raw_columns[i];
          $scope.change(tcm);
          if (tcm.is_duplicate) {
            return true;
          }
        }
        return false;
      };

      /*
       * empty_fields_present: used to disable or enable the 'show & review
       *   mappings' button.
       */
      $scope.empty_fields_present = function () {
        return Boolean(_.find($scope.raw_columns, {suggestion: ''}));
      };

      /*
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

        function compare_fields(x, y) {
          return x.header == y.suggestion && x.inventory_type == y.suggestion_table_name;
        }

        return _.intersectionWith(required_fields, $scope.raw_columns, compare_fields).length > 0;
      };

      $scope.backToMapping = function () {
        $scope.review_mappings = false;
        $scope.show_mapped_buildings = false;
      };

      /**
       * open_cleansing_modal: modal to present data cleansing warnings and errors
       */
      $scope.open_cleansing_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/cleansing_modal.html',
          controller: 'cleansing_controller',
          size: 'lg',
          resolve: {
            cleansingResults: function () {
              return cleansing_service.get_cleansing_results($scope.import_file.id);
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

        $scope.duplicates_present();
        $scope.duplicates = $filter('filter')($scope.raw_columns, {is_duplicate: true});
        $scope.duplicates = $filter('orderBy')($scope.duplicates, 'suggestion', false);
        $scope.valids = $filter('filter')($scope.raw_columns, {is_duplicate: false});

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
        var dataModalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/data_upload_modal.html',
          controller: 'data_upload_modal_controller',
          resolve: {
            cycles: cycles,
            step: function () {
              return step;
            },
            dataset: function () {
              return ds;
            }
          }
        });

      };

      $scope.MAP_copy = 'A \'check\' indicates you want to map a data field header from your import file to either a standard header from the Building Energy Data Exchange Specification (BEDES) or to a custom header of your choice. Unchecked rows will be ignored for mapping purposes and the data will be imported with the header from your import file.';

      $scope.BEDES_copy = 'A Green check in this column indicates the mapping is done to a standard field in the BEDES specification.';

      $scope.VALIDATE_copy = 'Indicates whether data mapping was successful, if there\'s invalid data in your columns, or a duplicate field header mappings that need to be re-mapped to a unique BEDES/non-BEDES field. ';

    }]);
