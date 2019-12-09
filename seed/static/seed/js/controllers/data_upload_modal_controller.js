/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
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
 * ng-switch-when="14" == Successful upload! [BuildingSync]
 */
angular.module('BE.seed.controller.data_upload_modal', [])
  .controller('data_upload_modal_controller', [
    '$http',
    '$scope',
    '$uibModalInstance',
    '$log',
    '$timeout',
    'uiGridConstants',
    'uploader_service',
    '$state',
    'dataset_service',
    'mapping_service',
    'matching_service',
    'meters_service',
    'inventory_service',
    'spinner_utility',
    'step',
    'dataset',
    'cycles',
    'organization',
    function (
      $http,
      $scope,
      $uibModalInstance,
      $log,
      $timeout,
      uiGridConstants,
      uploader_service,
      $state,
      dataset_service,
      mapping_service,
      matching_service,
      meters_service,
      inventory_service,
      spinner_utility,
      step,
      dataset,
      cycles,
      organization
    ) {
      $scope.cycles = cycles.cycles;
      if ($scope.cycles.length) $scope.selectedCycle = $scope.cycles[0];
      $scope.step_10_style = 'info';
      $scope.step_10_title = 'load more data';
      $scope.step = {
        number: step
      };
      $scope.pm_buttons_enabled = true;
      $scope.pm_error_alert = false;
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
       * progress: int or float - the progress bar value, i.e. percentage complete
       * complete: bool - true when the upload has finished
       */
      $scope.uploader = {
        invalid_extension_alert: false,
        invalid_geojson_extension_alert: false,
        invalid_xml_extension_alert: false,
        invalid_xml_zip_extension_alert: false,
        in_progress: false,
        progress: 0,
        complete: false,
        status_message: ''
      };

      /**
       * Tell the backend that the mapping is done and start the next step
       */
      $scope.save_mappings = function () {
        // API request to tell backend that it is finished with the mappings
        $http.put('/api/v2/import_files/' + $scope.dataset.import_file_id + '/mapping_done/', {}, {
          params: {
            organization_id: $scope.organization.org_id
          }
        }).then(function () {
          $scope.goto_step(7);
          $scope.find_matches();
        });
      };

      /**
       * goto_step: changes the step of the modal, i.e. name dataset -> upload ...
       * step: int - used with the `ng-switch` in the DOM to change state
       */
      $scope.goto_step = function (step) {
        $scope.step.number = step;
      };

      $scope.cycleChanged = function (selected) {
        $scope.selectedCycle = selected;
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
      /**
       * cancel: dismissed the modal, routes to the dismiss function of the parent
       *  scope
       */
      $scope.cancel = function () {
        // If step 15, PM Meter Usage import confirmation was not accepted by user, so delete file
        if ($scope.step.number == 15) {
          dataset_service.delete_file($scope.file_id).then(function (/*results*/) {
            $uibModalInstance.dismiss('cancel');
          });
        } else {
          $uibModalInstance.dismiss('cancel');
        }
      };
      /**
       * create_dataset: uses the `uploader_service` to create a new data set. If
       *  there is an error, i.e. the request fails or the data set name is
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
        $scope.proposed_imports_options = {
          data: result.proposed_imports,
          columnDefs: [{
            field: 'pm_property_id',
            displayName: 'PM Property ID',
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

      var present_meter_import_error = function (/*error*/) {
        $scope.pm_meter_import_error = true;
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
            // add variables to identify buildingsync bulk uploads
            $scope.building_sync_files = (file.source_type === 'BuildingSync');
            $scope.bulk_upload = (_.last(file.filename.split('.')) === 'zip');
            break;

          case 'upload_in_progress':
            $scope.uploader.in_progress = true;
            if (file.source_type === 'BuildingSync') {
              $scope.uploader.progress = 100 * progress.loaded / progress.total;
            } else {
              $scope.uploader.progress = 25 * progress.loaded / progress.total;
            }
            break;

          case 'upload_complete':
            var current_step = $scope.step.number;
            $scope.uploader.status_message = 'upload complete';
            $scope.dataset.filename = file.filename;
            $scope.step_14_message = null;

            if (file.source_type === 'BuildingSync') {
              $scope.uploader.complete = true;
              $scope.uploader.in_progress = false;
              $scope.uploader.progress = 100;
              $scope.step.number = 14;
              $scope.step_14_message = (_.size(file.message.warnings) > 0) ? file.message.warnings : null;
            } else if (file.source_type === 'PM Meter Usage') {
              $scope.cycle_id = file.cycle_id;
              $scope.file_id = file.file_id;

              // Hardcoded as this is a 2 step process: upload & analyze
              $scope.uploader.progress = 50;
              $scope.uploader.status_message = 'analyzing file';
              meters_service
                .parsed_meters_confirmation(file.file_id, $scope.organization.org_id)
                .then(present_parsed_meters_confirmation)
                .catch(present_meter_import_error);
            } else {
              $scope.dataset.import_file_id = file.file_id;

              // Assessed Data; upload is step 2; PM import is currently treated as such, and is step 13
              if (current_step === 2 || current_step === 13) {
                save_raw_assessed_data(file.file_id, file.cycle_id, false);
              }
              // Portfolio Data
              if (current_step === 4) {
                save_map_match_PM_data(file.file_id, file.cycle_id);
              }
            }
            break;
        }

        $scope.accept_meters = function (file_id, cycle_id) {
          $scope.uploader.in_progress = true;
          save_raw_assessed_data(file_id, cycle_id, true);
        };

        // $apply() or $digest() needed maybe because of this:
        // https://github.com/angular-ui/bootstrap/issues/1798
        // otherwise alert doesn't show unless modal is interacted with
        _.defer(function () {
          $scope.$apply();
        });
      };

      /**
       * save_map_match_PM_data: saves, maps, and matches PM data
       *
       * @param {string} file_id: the id of the import file
       * @param {string} cycle_id: the id of the cycle
       */
      var save_map_match_PM_data = function (file_id, cycle_id) {
        $scope.uploader.status_message = 'saving energy data';
        $scope.uploader.progress = 25;
        uploader_service.save_raw_data(file_id, cycle_id)
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
       * save_raw_assessed_data: saves Assessed data
       *
       * @param {string} file_id: the id of the import file
       * @param cycle_id
       * @param is_meter_data
       */
      var save_raw_assessed_data = function (file_id, cycle_id, is_meter_data) {
        $scope.uploader.status_message = 'saving data';
        $scope.uploader.progress = 0;
        uploader_service.save_raw_data(file_id, cycle_id).then(function (data) {
          var progress = _.clamp(data.progress, 0, 100);
          uploader_service.check_progress_loop(data.progress_key, progress, 1 - (progress / 100), function (progress_data) {
            $scope.uploader.status_message = 'saving complete';
            $scope.uploader.progress = 100;
            if (is_meter_data) {
              $scope.import_results_options = meter_import_results(progress_data.message);
              $scope.step.number = 16;
            } else {
              $scope.step.number = 3;
            }
          }, function (data) {
            $log.error(data.message);
            if (_.has(data, 'stacktrace')) $log.error(data.stacktrace);
            $scope.step_12_error_message = data.message;
            $scope.step.number = 12;
          }, $scope.uploader);
        });
      };

      /**
       * find_matches: finds matches for buildings within an import file
       */
      $scope.find_matches = function () {
        matching_service.start_system_matching($scope.dataset.import_file_id).then(function (data) {
          if (_.includes(['error', 'warning'], data.status)) {
            $scope.uploader.complete = true;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 0;
            $scope.step.number = 10;
            $scope.step_10_style = 'danger';
            $scope.step_10_error_message = data.message;
            $scope.step_10_title = data.message;
          } else {
            uploader_service.check_progress_loop(data.progress_key, data.progress, 1, function () {
              inventory_service.get_matching_and_geocoding_results($scope.dataset.import_file_id).then(function (result_data) {
                $scope.duplicate_property_states = result_data.properties.duplicates;
                $scope.duplicate_tax_lot_states = result_data.tax_lots.duplicates;
                $scope.duplicates_of_existing_property_states = result_data.properties.duplicates_of_existing;
                $scope.duplicates_of_existing_taxlot_states = result_data.tax_lots.duplicates_of_existing;
                $scope.import_file_records = result_data.import_file_records;

                $scope.properties_geocoded_high_confidence = result_data.properties.geocoded_high_confidence;
                $scope.properties_geocoded_low_confidence = result_data.properties.geocoded_low_confidence;
                $scope.properties_geocoded_manually = result_data.properties.geocoded_manually;
                $scope.properties_geocode_not_possible = result_data.properties.geocode_not_possible;

                $scope.tax_lots_geocoded_high_confidence = result_data.tax_lots.geocoded_high_confidence;
                $scope.tax_lots_geocoded_low_confidence = result_data.tax_lots.geocoded_low_confidence;
                $scope.tax_lots_geocoded_manually = result_data.tax_lots.geocoded_manually;
                $scope.tax_lots_geocode_not_possible = result_data.tax_lots.geocode_not_possible;

                $scope.matched_properties = result_data.properties.matched;
                $scope.unmatched_properties = result_data.properties.unmatched;
                $scope.matched_taxlots = result_data.tax_lots.matched;
                $scope.unmatched_taxlots = result_data.tax_lots.unmatched;
                $scope.uploader.complete = true;
                $scope.uploader.in_progress = false;
                $scope.uploader.progress = 0;
                $scope.uploader.status_message = '';
                if ($scope.matched_properties + $scope.matched_taxlots > 0) {
                  $scope.step.number = 8;
                } else {
                  $scope.step.number = 10;
                }
              });
            }, function () {
              // Do nothing
            }, $scope.uploader);
          }
        });
      };

      $scope.get_pm_report_template_names = function (pm_username, pm_password) {
        spinner_utility.show();
        $scope.pm_buttons_enabled = false;
        $http.post('/api/v2_1/portfolio_manager/template_list/', {
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
        $http.post('/api/v2_1/portfolio_manager/report/', {
          username: pm_username,
          password: pm_password,
          template: pm_template
        }).then(function (response) {
          response = $http.post('/api/v2/upload/create_from_pm_import/', {
            properties: response.data.properties,
            import_record_id: $scope.dataset.id
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
