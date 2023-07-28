/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * data_upload_modal_controller: the AngularJS controller for the data upload modal.
 *
 * The numbers corresponding to ``step.number`` are reflected in
 * modal title changes like so:
 *
 * ng-switch-when="1" == Create a New Data Set.
 * ng-switch-when="2" == Upload your building list.
 * ng-switch-when="3" == Successful upload!
 * ng-switch-when="4" == Upload your energy data.
 * ng-switch-when="5" == Successful upload!
 * ng-switch-when="6" == What type of .csv file would you like to upload?
 * ng-switch-when="7" == Finding building matches.
 * ng-switch-when="8" == 450 building matches found.
 * ng-switch-when="9" == Add files to {$ dataset.name $}
 * ng-switch-when="10" == No matches found
 * ng-switch-when="11" == Confirm Save Mappings?
 * ng-switch-when="12" == Error Processing Data
 * ng-switch-when="13" == Portfolio Manager Import
 */
angular.module('BE.seed.controller.data_upload_modal', [])
  .controller('data_upload_modal_controller', [
    '$http',
    '$scope',
    '$rootScope',
    '$uibModalInstance',
    '$log',
    '$timeout',
    'uiGridConstants',
    'uploader_service',
    '$state',
    'audit_template_service',
    'dataset_service',
    'mapping_service',
    'matching_service',
    'inventory_service',
    'spinner_utility',
    'step',
    'dataset',
    'cycles',
    'organization',
    'urls',
    function (
      $http,
      $scope,
      $rootScope,
      $uibModalInstance,
      $log,
      $timeout,
      uiGridConstants,
      uploader_service,
      $state,
      audit_template_service,
      dataset_service,
      mapping_service,
      matching_service,
      inventory_service,
      spinner_utility,
      step,
      dataset,
      cycles,
      organization,
      urls
    ) {
      $scope.urls = urls;
      $scope.cycles = cycles.cycles;
      var cached_cycle = inventory_service.get_last_cycle();
      $scope.selectedCycle = _.find(cycles.cycles, {id: cached_cycle}) || _.first(cycles.cycles);
      $scope.multipleCycleUpload = false;
      $scope.show_help = false;

      $scope.step_10_style = 'info';
      $scope.step_10_title = 'load more data';
      $scope.step = {
        number: step
      };
      $scope.pm_buttons_enabled = true;
      $scope.pm_error_alert = false;
      // Initial value is 0, after a response is returned it will be set to true or false
      $scope.import_file_reusable_for_meters = 0;
      /**
       * dataset: holds the state of the data set
       * name: string - the data set name
       * disabled: return bool - when true: disables the `Create Data Set` button
       * alert: bool - when true: shows the bootstrap alert `the file name is
       *  already in use`
       * id: int - set with `create_dataset` resolve promise, is the id of the
       *  newly created data set
       * file: the file being upload file.filename is the file's name
       */
      $scope.organization = organization;
      $scope.dataset = {
        name: '',
        disabled: function () {
          var name = $scope.dataset.name || '';
          return name.length === 0;
        },
        alert: false,
        id: 0,
        filename: '',
        import_file_id: 0
      };

      /**
       * uploader: hold the state of the upload.
       * invalid_extension_alert: bool - hides or shows the bootstrap alert for csv/xls/xlsx files
       * invalid_geojson_extension_alert: bool - hides or shows the bootstrap alert for geojson/json files
       * invalid_xml_extension_alert: bool - hides or shows the bootstrap alert for xml files
       * invalid_xml_zip_extension_alert: bool - hides or shows the bootstrap alert for xml/zip files
       * in_progress: bool - when true: shows the progress bar and hides the
       *  upload button. when false: hides the progress bar and shows the upload
       *  button.
       * progress: int or float - the progress bar value, i.e., percentage complete
       * complete: bool - true when the upload has finished
       * status_message: str - status of the task
       * progress_last_updated: null | int - when not null it indicates the last time the progress bar changed (UNIX Epoch in ms)
       * progress_last_checked: null | int - when not null it indicates the last time the progress was checked (UNIX Epoch in ms)
       */
      $scope.uploader = {
        invalid_extension_alert: false,
        invalid_geojson_extension_alert: false,
        invalid_xml_extension_alert: false,
        invalid_xml_zip_extension_alert: false,
        in_progress: false,
        progress: 0,
        complete: false,
        status_message: '',
        progress_last_updated: null,
        progress_last_checked: null
      };
      $scope.sub_uploader = {
        progress: 0,
        status_message: ''
      };

      /**
       * Tell the backend that the mapping is done and start the next step
       */
      $scope.save_mappings = function () {
        // API request to tell backend that it is finished with the mappings
        $http.post('/api/v3/import_files/' + $scope.dataset.import_file_id + '/mapping_done/', {}, {
          params: {
            organization_id: $scope.organization.org_id
          }
        }).then(function () {
          $scope.goto_step(7);
          $scope.find_matches();
        });
      };

      /**
       * goto_step: changes the step of the modal, i.e., name dataset -> upload ...
       * step: int - used with the `ng-switch` in the DOM to change state
       */
      $scope.goto_step = function (step) {
        $scope.step.number = step;
      };

      $scope.toggleMultipleCycleUpload = function () {
        $scope.multipleCycleUpload = !$scope.multipleCycleUpload;
      };

      $scope.cycleChanged = function (selected) {
        $scope.selectedCycle = selected;
        inventory_service.save_last_cycle(selected.id);
      };

      /**
       * close: closes the modal, routes to the close function of the parent scope
       */
      $scope.close = function () {
        $uibModalInstance.close();
      };
      $scope.goto_data_mapping = function () {
        $uibModalInstance.close();
        $state.go('mapping', {importfile_id: $scope.dataset.import_file_id});
      };
      $scope.view_my_properties = function () {
        $uibModalInstance.close();
        $state.go('inventory_list', {inventory_type: 'properties'});
      };
      $scope.reset_mapquest_api_key = function () {
        $uibModalInstance.close();
        $state.go('organization_settings', {organization_id: $scope.organization.org_id});
      };
      /**
       * cancel: dismissed the modal, routes to the dismiss function of the parent
       *  scope
       */
      $scope.cancel = function () {
        // If step 15, PM Meter Usage import confirmation was not accepted by user, so delete file
        if ($scope.step.number == 15 && $scope.file_id) {
          dataset_service.delete_file($scope.file_id).then(function (/*results*/) {
            $uibModalInstance.dismiss('cancel');
          });
        } else {
          $uibModalInstance.dismiss('cancel');
        }
      };
      /**
       * create_dataset: uses the `uploader_service` to create a new data set. If
       *  there is an error, i.e., the request fails or the data set name is
       *  already taken, then the bootstrap alert is shown
       */
      $scope.create_dataset = function (dataset_name) {
        uploader_service.create_dataset(dataset_name).then(function (data) {
          $scope.goto_step(2);
          $scope.dataset.id = data.id;
          $scope.dataset.name = data.name;
          $scope.uploader.status_message = 'uploading file';
        }, function (status) {
          var message = status.message || '';
          if (message === 'name already in use') {
            $scope.dataset.alert = true;
          }
        });
      };

      var grid_rows_to_display = function (data) {
        return Math.min(data.length, 5);
      };

      var present_parsed_meters_confirmation = function (result) {
        $scope.proposed_meters_count = result.proposed_imports.length;
        $scope.proposed_meters_count_string = $scope.proposed_meters_count > 1 ? `${$scope.proposed_meters_count} Meters` : `${$scope.proposed_meters_count} Meter`;
        $scope.proposed_properties_count = new Set(result.proposed_imports.map((meter) => meter.pm_property_id)).size;
        $scope.proposed_properties_count_string = $scope.proposed_properties_count > 1 ? `${$scope.proposed_properties_count} Properties` : `${$scope.proposed_properties_count} Property`;
        $scope.unlinkable_properties_count = result.unlinkable_pm_ids.length;
        $scope.unlinkable_properties_count_string = $scope.unlinkable_properties_count > 1 ? `${$scope.unlinkable_properties_count} Properties` : `${$scope.unlinkable_properties} Property`;
        $scope.proposed_imports_options = {
          data: result.proposed_imports,
          columnDefs: [{
            field: 'pm_property_id',
            displayName: 'PM Property ID',
            enableHiding: false,
            type: 'string'
          }, {
            field: 'cycles',
            displayName: 'Cycles',
            enableHiding: false,
            type: 'string'
          }, {
            field: 'source_id',
            displayName: 'PM Meter ID',
            enableHiding: false,
            type: 'string'
          }, {
            field: 'type',
            enableHiding: false
          }, {
            field: 'incoming',
            enableHiding: false
          }],
          enableColumnResizing: true,
          enableHorizontalScrollbar: uiGridConstants.scrollbars.NEVER,
          enableVerticalScrollbar: result.proposed_imports.length <= 5 ? uiGridConstants.scrollbars.NEVER : uiGridConstants.scrollbars.WHEN_NEEDED,
          minRowsToShow: grid_rows_to_display(result.proposed_imports)
        };

        $scope.parsed_type_units_options = {
          data: result.validated_type_units,
          columnDefs: [{
            field: 'parsed_type',
            enableHiding: false
          }, {
            field: 'parsed_unit',
            enableHiding: false
          }],
          enableColumnResizing: true,
          enableHorizontalScrollbar: uiGridConstants.scrollbars.NEVER,
          enableVerticalScrollbar: result.validated_type_units.length <= 5 ? uiGridConstants.scrollbars.NEVER : uiGridConstants.scrollbars.WHEN_NEEDED,
          minRowsToShow: grid_rows_to_display(result.validated_type_units)
        };

        $scope.unlinkable_pm_ids_options = {
          data: result.unlinkable_pm_ids,
          columnDefs: [{
            field: 'portfolio_manager_id',
            displayName: 'PM Property ID',
            enableHiding: false
          }],
          enableHorizontalScrollbar: uiGridConstants.scrollbars.NEVER,
          enableVerticalScrollbar: result.unlinkable_pm_ids.length <= 5 ? uiGridConstants.scrollbars.NEVER : uiGridConstants.scrollbars.WHEN_NEEDED,
          minRowsToShow: grid_rows_to_display(result.unlinkable_pm_ids)
        };

        $scope.uploader.in_progress = false;
        $scope.uploader.progress = 0;

        var modal_element = angular.element(document.getElementsByClassName('modal-dialog'));
        modal_element.addClass('modal-lg');

        $scope.step.number = 15;
      };

      var present_meter_import_error = function (message) {
        $scope.pm_meter_import_error = message;
        $scope.uploader.in_progress = false;
        $scope.uploader.progress = 0;

        // Go to step 15 as "Dismiss"ing from here will delete the file.
        $scope.step.number = 15;
      };

      /**
       * uploaderfunc: the callback function passed to sdUploader. Depending on
       *  the `event_message` from sdUploader, it will change the state of the
       *  modal, show the `invalid_extension` alert, and update the progress bar.
       */
      $scope.uploaderfunc = function (event_message, file, progress) {
        switch (event_message) {
          case 'invalid_extension':
            $scope.uploader.invalid_extension_alert = true;
            $scope.uploader.invalid_geojson_extension_alert = false;
            $scope.uploader.invalid_xml_extension_alert = false;
            $scope.uploader.invalid_xml_zip_extension_alert = false;
            break;

          case 'invalid_geojson_extension':
            $scope.uploader.invalid_extension_alert = false;
            $scope.uploader.invalid_geojson_extension_alert = true;
            $scope.uploader.invalid_xml_extension_alert = false;
            $scope.uploader.invalid_xml_zip_extension_alert = false;
            break;

          case 'invalid_xml_extension':
            $scope.uploader.invalid_extension_alert = false;
            $scope.uploader.invalid_geojson_extension_alert = false;
            $scope.uploader.invalid_xml_extension_alert = true;
            $scope.uploader.invalid_xml_zip_extension_alert = false;
            break;

          case 'invalid_xml_zip_extension':
            $scope.uploader.invalid_extension_alert = false;
            $scope.uploader.invalid_geojson_extension_alert = false;
            $scope.uploader.invalid_xml_extension_alert = false;
            $scope.uploader.invalid_xml_zip_extension_alert = true;
            break;

          case 'upload_submitted':
            $scope.dataset.filename = file.filename;
            $scope.uploader.in_progress = true;
            $scope.uploader.status_message = 'uploading file';
            break;

          case 'upload_error':
            $scope.step_12_error_message = file.error;
            $scope.step.number = 12;
            break;

          case 'upload_in_progress':
            $scope.uploader.in_progress = true;
            $scope.uploader.progress = 25 * progress.loaded / progress.total;
            break;

          case 'upload_complete':
            var current_step = $scope.step.number;
            $scope.uploader.status_message = 'upload complete';
            $scope.dataset.filename = file.filename;
            $scope.source_type = file.source_type;

            if (file.source_type === 'PM Meter Usage') {
              $scope.cycle_id = file.cycle_id;
              $scope.file_id = file.file_id;

              // Hardcoded as this is a 2 step process: upload & analyze
              $scope.uploader.progress = 50;
              $scope.uploader.status_message = 'analyzing file';
              uploader_service
                .pm_meters_preview(file.file_id, $scope.organization.org_id)
                .then(present_parsed_meters_confirmation)
                .catch((err) => present_meter_import_error(err));
            } else {
              $scope.dataset.import_file_id = file.file_id;

              // Assessed Data; upload is step 2; PM import is currently treated as such, and is step 13
              if (current_step === 2 || current_step === 13) {
                // if importing BuildingSync, validate then save, otherwise just save
                if (file.source_type === 'BuildingSync Raw') {
                  validate_use_cases_then_save(file.file_id, file.cycle_id);
                } else {
                  save_raw_assessed_data(file.file_id, file.cycle_id, false, $scope.multipleCycleUpload);
                }
              }
              // Portfolio Data
              if (current_step === 4) {
                save_map_match_PM_data(file.file_id, file.cycle_id, $scope.multipleCycleUpload);
              }
            }
            break;
        }

        // $apply() or $digest() needed maybe because of this:
        // https://github.com/angular-ui/bootstrap/issues/1798
        // otherwise alert doesn't show unless modal is interacted with
        _.defer(function () {
          $scope.$apply();
        });
      };

      $scope.accept_meters = function (file_id, cycle_id) {
        file_id = file_id || $scope.dataset.import_file_id;
        cycle_id = cycle_id || $scope.selectedCycle.id;
        $scope.uploader.in_progress = true;
        save_raw_assessed_data(file_id, cycle_id, true);
        $rootScope.$emit('datasets_updated');
      };

      /**
       * save_map_match_PM_data: saves, maps, and matches PM data
       *
       * @param {string} file_id: the id of the import file
       * @param {string} cycle_id: the id of the cycle
       * @param {boolean} multiple_cycle_upload: whether records can be imported into multiple cycles
       */
      var save_map_match_PM_data = function (file_id, cycle_id, multiple_cycle_upload = false) {
        $scope.uploader.status_message = 'saving energy data';
        $scope.uploader.progress = 25;
        uploader_service.save_raw_data(file_id, cycle_id, multiple_cycle_upload)
          .then(function (data) {
            // resolve save_raw_data promise
            monitor_save_raw_data(data.progress_key, file_id);
          });
      };

      /**
       * monitor_save_raw_data: updates progress bar from 25% to 50%,
       *   called by save_map_match_PM_data
       *
       * @param {string} progress_key: key
       * @param {string} file_id: id of file
       */
      var monitor_save_raw_data = function (progress_key, file_id) {
        uploader_service.check_progress_loop(progress_key, 25, 0.25, function () {
          $scope.uploader.status_message = 'auto-mapping energy data';
          mapping_service.start_mapping(file_id).then(function (data) {
            monitor_mapping(data.progress_key, file_id);
          });
        }, function () {
          // Do nothing
        }, $scope.uploader);
      };

      /**
       * monitor_mapping: called by monitor_save_raw_data, updates progress bar
       *   from 50% to 75%
       *
       * @param {string} progress_key: key
       * @param {string} file_id: id of file
       */
      var monitor_mapping = function (progress_key, file_id) {
        uploader_service.check_progress_loop(progress_key, 50, 0.25, function () {
          $scope.uploader.status_message = 'auto-matching energy data';
          matching_service.start_system_matching(file_id).then(function (data) {
            monitor_matching(data.progress_key, file_id);
          });
        }, function () {
          // Do nothing
        }, $scope.uploader);
      };

      /**
       * monitor_matching: called by monitor_mapping, updates progress bar
       *   from 75% to 100%, then shows the PM upload completed
       *
       * @param {string} progress_key: key
       */
      var monitor_matching = function (progress_key) {
        uploader_service.check_progress_loop(progress_key, 75, 0.25, function () {
          $scope.uploader.complete = true;
          $scope.uploader.in_progress = false;
          $scope.uploader.progress = 1;
          $scope.step.number = 5;
        }, function () {
          // Do nothing
        }, $scope.uploader);
      };

      var meter_import_results = function (results) {
        var column_defs = [{
          field: 'pm_property_id',
          displayName: 'PM Property ID',
          enableHiding: false,
          type: 'string'
        }, {
          field: 'cycles',
          displayName: 'Cycles',
          enableHiding: false,
          type: 'string'
        }, {
          field: 'source_id',
          displayName: 'Portfolio Manager Meter ID',
          enableHiding: false
        }, {
          field: 'type',
          enableHiding: false
        }, {
          field: 'incoming',
          enableHiding: false
        }, {
          field: 'successfully_imported',
          enableHiding: false
        }];

        if (_.has(results, '[0].errors')) {
          column_defs.push({
            field: 'errors',
            enableHiding: false
          });
        }

        return {
          data: results,
          columnDefs: column_defs,
          enableColumnResizing: true,
          enableHorizontalScrollbar: uiGridConstants.scrollbars.NEVER,
          enableVerticalScrollbar: results.length <= 5 ? uiGridConstants.scrollbars.NEVER : uiGridConstants.scrollbars.WHEN_NEEDED,
          minRowsToShow: grid_rows_to_display(results)
        };
      };

      /**
       * validate_use_cases_then_save: validates BuildingSync files for use cases
       * before saving the data
       *
       * @param {string} file_id: the id of the import file
       * @param cycle_id
       */
      var validate_use_cases_then_save = function (file_id, cycle_id) {
        $scope.uploader.status_message = 'validating data';
        $scope.uploader.progress = 0;

        var successHandler = function (progress_data) {
          $scope.uploader.complete = false;
          $scope.uploader.in_progress = true;
          $scope.uploader.status_message = 'validation complete; starting to save data';
          $scope.uploader.progress = 100;

          var result = JSON.parse(progress_data.message);
          $scope.buildingsync_valid = result.valid;
          $scope.buildingsync_issues = result.issues;
          for (const file in $scope.buildingsync_issues) {
            let schema_errors = [];
            for (const i in $scope.buildingsync_issues[file].schema_errors) {
              let error = $scope.buildingsync_issues[file].schema_errors[i];
              schema_errors.push([error.message, error.path].join(' - '));
            }
            $scope.buildingsync_issues[file].schema_errors = schema_errors;
          }

          // if validation failed, end the import flow here; otherwise continue
          if ($scope.buildingsync_valid !== true) {
            $scope.step_12_error_message = 'Failed to validate uploaded BuildingSync file(s)';
            $scope.step_12_buildingsync_validation_error = true;
            $scope.step.number = 12;
          } else {
            // successfully passed validation, save the data
            save_raw_assessed_data(file_id, cycle_id, false);

          }
        };

        var errorHandler = function (data) {
          $log.error(data.message);
          if (data.stacktrace) $log.error(data.stacktrace);
          $scope.step_12_error_message = data.data ? data.data.message : data.message;
          $scope.step.number = 12;
        };

        uploader_service.validate_use_cases(file_id)
          .then(function (data) {
            var progress = _.clamp(data.progress, 0, 100);
            uploader_service.check_progress_loop(
              data.progress_key,
              progress, 1 - (progress / 100),
              successHandler,
              errorHandler,
              $scope.uploader
            );
          });
      };

      $scope.reuse_import_file_to_import_meters = function () {
        $scope.preparing_pm_meters_preview = true;
        dataset_service.reuse_inventory_file_for_meters($scope.dataset.import_file_id).then(function (data) {
          $scope.dataset.import_file_id = data.import_file_id;
          $scope.uploader.progress = 50;
          $scope.uploader.status_message = 'analyzing file';
          uploader_service
            .pm_meters_preview($scope.dataset.import_file_id, $scope.organization.org_id)
            .then(present_parsed_meters_confirmation)
            .then(function () {
              $scope.preparing_pm_meters_preview = false
            })
            .catch((err) => present_meter_import_error(err));
        });
      };

      /**
       * save_raw_assessed_data: saves Assessed data
       *
       * @param {string} file_id: the id of the import file
       * @param cycle_id
       * @param is_meter_data
       * @param multiple_cycle_upload
       */
      var save_raw_assessed_data = function (file_id, cycle_id, is_meter_data, multiple_cycle_upload = false) {
        $scope.uploader.status_message = 'saving data';
        $scope.uploader.progress = 0;
        uploader_service.save_raw_data(file_id, cycle_id, multiple_cycle_upload).then(function (data) {
          var progress = _.clamp(data.progress, 0, 100);
          uploader_service.check_progress_loop(data.progress_key, progress, 1 - (progress / 100), function (progress_data) {
            $scope.uploader.status_message = 'saving complete';
            $scope.uploader.progress = 100;
            if (is_meter_data) {
              $scope.import_meters_count = progress_data.message.length;
              $scope.import_meters_count_string = $scope.import_meters_count > 1 ? `${$scope.import_meters_count} Meters` : `${$scope.import_meters_count} Meter`;
              $scope.import_properties_count = new Set(progress_data.message.map((meter) => meter.pm_property_id)).size;
              $scope.import_properties_count_string = $scope.import_properties_count > 1 ? `${$scope.import_properties_count} Properties` : `${$scope.import_properties_count} Property`;
              $scope.import_results_options = meter_import_results(progress_data.message);
              $scope.step.number = 16;
            } else {
              $scope.step.number = 3;
            }
          }, function (data) {
            $log.error(data.message);
            if (_.has(data, 'stacktrace')) $log.error(data.stacktrace);
            $scope.step_12_error_message = data.data ? data.data.message : data.message;
            $scope.step.number = 12;
          }, $scope.uploader);
        });
      };

      /**
       * find_matches: finds matches for buildings within an import file
       */
      $scope.find_matches = function () {

        matching_service.start_system_matching($scope.dataset.import_file_id).then(function (data) {
          $scope.step_10_mapquest_api_error = false;

          // helper function to set scope parameters for when the task fails
          const handleSystemMatchingError = function (data) {
            $scope.uploader.complete = true;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 0;
            $scope.step.number = 10;
            $scope.step_10_style = 'danger';
            $scope.step_10_error_message = data.progress_data.message;
            $scope.step_10_title = data.progress_data.message;
          };

          if (_.includes(['error', 'warning'], data.progress_data.status)) {
            handleSystemMatchingError(data);
          } else {
            const progress_argument = {
              progress_key: data.progress_data.progress_key,
              offset: data.progress_data.progress,
              multiplier: 1,
              progress_bar_obj: $scope.uploader
            };
            const sub_progress_argument = {
              progress_key: data.sub_progress_data.progress_key,
              offset: data.sub_progress_data.progress,
              multiplier: 1,
              progress_bar_obj: $scope.sub_uploader
            };
            uploader_service.check_progress_loop_main_sub(progress_argument, function (progress_data) {
              inventory_service.get_matching_and_geocoding_results($scope.dataset.import_file_id).then(function (result_data) {
                $scope.import_file_records = result_data.import_file_records;
                $scope.multipleCycleUpload = result_data.multiple_cycle_upload;

                $scope.property_initial_incoming = result_data.properties.initial_incoming;
                $scope.property_duplicates_against_existing = result_data.properties.duplicates_against_existing;
                $scope.property_duplicates_within_file = result_data.properties.duplicates_within_file;
                $scope.property_merges_against_existing = result_data.properties.merges_against_existing;
                $scope.property_merges_between_existing = result_data.properties.merges_between_existing;
                $scope.property_merges_within_file = result_data.properties.merges_within_file;
                $scope.property_new = result_data.properties.new;

                $scope.properties_geocoded_high_confidence = result_data.properties.geocoded_high_confidence;
                $scope.properties_geocoded_low_confidence = result_data.properties.geocoded_low_confidence;
                $scope.properties_geocoded_manually = result_data.properties.geocoded_manually;
                $scope.properties_geocode_not_possible = result_data.properties.geocode_not_possible;

                $scope.tax_lot_initial_incoming = result_data.tax_lots.initial_incoming;
                $scope.tax_lot_duplicates_against_existing = result_data.tax_lots.duplicates_against_existing;
                $scope.tax_lot_duplicates_within_file = result_data.tax_lots.duplicates_within_file;
                $scope.tax_lot_merges_against_existing = result_data.tax_lots.merges_against_existing;
                $scope.tax_lot_merges_between_existing = result_data.tax_lots.merges_between_existing;
                $scope.tax_lot_merges_within_file = result_data.tax_lots.merges_within_file;
                $scope.tax_lot_new = result_data.tax_lots.new;

                $scope.tax_lots_geocoded_high_confidence = result_data.tax_lots.geocoded_high_confidence;
                $scope.tax_lots_geocoded_low_confidence = result_data.tax_lots.geocoded_low_confidence;
                $scope.tax_lots_geocoded_manually = result_data.tax_lots.geocoded_manually;
                $scope.tax_lots_geocode_not_possible = result_data.tax_lots.geocode_not_possible;

                $scope.uploader.complete = true;
                $scope.uploader.in_progress = false;
                $scope.uploader.progress = 0;
                $scope.uploader.status_message = '';
                if (progress_data.file_info !== undefined) {
                  // this only occurs in buildingsync, where we are not actually merging properties
                  // thus we will always end up at step 10
                  $scope.step_10_style = 'danger';
                  $scope.step_10_file_message = 'Warnings and/or errors occurred while processing the file(s).';
                  $scope.match_issues = [];
                  for (let file_name in progress_data.file_info) {
                    $scope.match_issues.push({
                      file: file_name,
                      errors: progress_data.file_info[file_name].errors,
                      warnings: progress_data.file_info[file_name].warnings
                    });
                  }
                }

                // Toggle a meter import button if the imported file also has a meters tab
                dataset_service.check_meters_tab_exists($scope.dataset.import_file_id).then(function (result) {
                  $scope.import_file_reusable_for_meters = result.data || false;
                });

                // If merges against existing exist, provide slightly different feedback
                if ($scope.property_merges_against_existing + $scope.tax_lot_merges_against_existing > 0) {
                  $scope.step.number = 8;
                } else {
                  $scope.step.number = 10;
                }
                $state.go('dataset_list');
              });
            }, function (response) {
              handleSystemMatchingError(response.data);
              if ($scope.step_10_error_message.includes('MapQuest')) {
                $scope.step_10_mapquest_api_error = true;
              }
            }, sub_progress_argument);
          }
        });
      };

      $scope.get_pm_report_template_names = function (pm_username, pm_password) {
        spinner_utility.show();
        $scope.pm_buttons_enabled = false;
        $http.post('/api/v3/portfolio_manager/template_list/', {
          username: pm_username,
          password: pm_password
        }).then(function (response) {
          $scope.pm_error_alert = false;
          $scope.pm_templates = response.data.templates;
          if ($scope.pm_templates.length) $scope.pm_template = _.first($scope.pm_templates);
          return response.data;
        }).catch(function (error) {
          $scope.pm_error_alert = 'Error: ' + error.data.message;
        }).finally(function () {
          spinner_utility.hide();
          $scope.pm_buttons_enabled = true;
        });
      };

      $scope.get_pm_report = function (pm_username, pm_password, pm_template) {
        spinner_utility.show();
        $scope.pm_buttons_enabled = false;
        $http.post('/api/v3/portfolio_manager/report/', {
          username: pm_username,
          password: pm_password,
          template: pm_template
        }).then(function (response) {
          response = $http.post('/api/v3/upload/create_from_pm_import/', {
            properties: response.data.properties,
            import_record_id: $scope.dataset.id,
            organization_id: $scope.organization.org_id
          });
          return response;
        }).then(function (response) {
          $scope.pm_error_alert = false;
          $scope.uploaderfunc('upload_complete', {
            filename: 'PortfolioManagerImport',
            file_id: response.data.import_file_id,
            source_type: 'PortfolioManager',
            cycle_id: $scope.selectedCycle.id
          });
        }).catch(function (error) {
          $scope.pm_error_alert = 'Error: ' + error.data.message;
        }).finally(function () {
          spinner_utility.hide();
          $scope.pm_buttons_enabled = true;
        });
      };

      $scope.export_issues = function (issues) {
        let data = ['File Name,Severity,Message'];
        let allowed_severities = {
          warnings: 'Warning',
          use_case_warnings: 'Use Case Warning',
          errors: 'Error',
          use_case_errors: 'Use Case Error',
          schema_errors: 'Schema Error'
        };
        for (const i in issues) {
          for (const severity in allowed_severities) {
            for (const issue in issues[i][severity]) {
              data.push([
                '"' + issues[i].file + '"',
                allowed_severities[severity],
                '"' + issues[i][severity][issue].replace(/\r?\n|\r/gm, ' ') + '"'
              ].join(','));
            }
          }
        }
        saveAs(new Blob([data.join('\r\n')], {type: 'text/csv'}), 'import_issues.csv');
      };

      $scope.export_meter_data = function (results, new_file_name) {
        let data = [results.columnDefs.map(c => c.displayName || c.name).join(',')];
        let keys = results.columnDefs.map(c => c.name);
        results.data.forEach(r => {
          let row = [];
          keys.forEach(k => row.push(r[k]));
          data.push(row.join(','));
        });
        saveAs(new Blob([data.join('\n')], {type: 'text/csv'}), new_file_name);
      }

      $scope.import_audit_template_buildings = function () {
        $scope.show_loading = true;
        audit_template_service.get_buildings($scope.organization.id, $scope.selectedCycle.id).then(function(response) {
          $scope.show_error = !response.success

          if ($scope.show_error) {
            $scope.error_message = response.message
          } else {
            const parsed_message = JSON.parse(response.message)
            
            if (parsed_message.length) {
              $scope.at_building_data = parsed_message
              setAtPropertyGrid();
            } else {
              $scope.show_error = true 
              $scope.error_message = 'Unable to find matching buildings between Audit Template and SEED Inventory'
            }
          }
          $scope.show_loading = false;
          $scope.step.number = 18;
        })
      }

      const setAtPropertyGrid = () => {
        $scope.atPropertySelectGridOptions = {
          data: $scope.at_building_data.map(building => ({
            'audit_template_building_id': building.audit_template_building_id,
            'email': building.email,
            'updated_at': building.updated_at,
            'property_view': building.property_view
          })),
          columnDefs: [
            {field: 'audit_template_building_id', displayName: 'Audit Template Building ID'},
            {field: 'email', displayName: 'Owner Email'},
            {field: 'updated_at', displayName: 'Updated At'},
            {field: 'property_view', visible: false}
          ],
          enableColumnMenus: false,
          enableColumnResizing: true,
          enableFiltering: true,
          enableSorting: true,
          enableHorizontalScrollbar: uiGridConstants.scrollbars.WHEN_NEEDED,
          enableVerticalScrollbar: uiGridConstants.scrollbars.WHEN_NEEDED,
          minRowsToShow: Math.min($scope.at_building_data.length, 25),
          rowHeight: '30px',
          onRegisterApi: (gridApi) => {
            $scope.gridApiAtPropertySelection = gridApi;
          }
        };
      }

      $scope.update_buildings_from_audit_template = () => {
        $scope.show_loading = true;
        const selected_property_views = $scope.gridApiAtPropertySelection.selection.getSelectedRows()
          .map(row => row['property_view'])
          .sort()
        const selected_data = $scope.at_building_data.filter(building =>  selected_property_views.includes(building.property_view))
        audit_template_service.batch_get_building_xml_and_update($scope.organization.id, $scope.selectedCycle.id, selected_data).then(response => {
          progress_key = response.progress_key
          uploader_service.check_progress_loop(progress_key, 0, 1, function (summary) {
            $scope.show_loading = false;
            $scope.at_upload_summary = summary.message
            $scope.step.number = 19
          }, function () {
            // do nothing
          }, $scope.uploader)
        })
      }

      $scope.rowsSelected = () => $scope.gridApiAtPropertySelection && $scope.gridApiAtPropertySelection.selection.getSelectedRows().length;

      /**
       * init: ran upon the controller load
       */
      var init = function () {
        angular.extend($scope.dataset, dataset);
        // set the `Data Set Name` input textbox to have key focus.
        $scope.step = {
          number: step
        };

        // goto matching progress
        if ($scope.step.number === 7) {
          $scope.find_matches();
        }
        $timeout(function () {
          angular.element('#inputDataUploadName').focus();

          //suppress the dismissing of the data upload modal when the background is clicked
          //the default dismiss leads to confusion about whether the upload was canceled - megha 1/22
          angular.element('.modal').off('click');

        }, 50);
      };
      init();

    }]);
