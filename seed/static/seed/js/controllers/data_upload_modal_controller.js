/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
 * ng-switch-when="8" == Add files to your Data Set.
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
    '$uibModalInstance',
    '$log',
    '$timeout',
    'uploader_service',
    '$state',
    'mapping_service',
    'matching_service',
    'inventory_service',
    'spinner_utility',
    'step',
    'dataset',
    'cycles',
    'organization',
    function ($http,
              $scope,
              $uibModalInstance,
              $log,
              $timeout,
              uploader_service,
              $state,
              mapping_service,
              matching_service,
              inventory_service,
              spinner_utility,
              step,
              dataset,
              cycles,
              organization) {
      $scope.cycles = cycles.cycles;
      if ($scope.cycles.length) $scope.selectedCycle = $scope.cycles[0];
      $scope.step_10_style = 'info';
      $scope.step_10_title = 'load more data';
      $scope.step = {
        number: step
      };
      $scope.pm_buttons_enabled = true;
      $scope.pm_error_alert = false;
      $scope.pm_warning_message = false;
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
       * invalid_extension_alert: bool - hides or shows the bootstrap alert
       * in_progress: bool - when true: shows the progress bar and hides the
       *  upload button. when false: hides the progress bar and shows the upload
       *  button.
       * progress: int or float - the progress bar value, i.e. percentage complete
       * complete: bool - true when the upload has finished
       */
      $scope.uploader = {
        invalid_extension_alert: false,
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
      /*$scope.goto_data_matching = function () {
        $uibModalInstance.close();
        $state.go('matching_list', {importfile_id: $scope.dataset.import_file_id, inventory_type: 'properties'});
      };*/
      $scope.view_my_properties = function () {
        $uibModalInstance.close();
        $state.go('inventory_list', {inventory_type: 'properties'});
      };
      /**
       * cancel: dismissed the modal, routes to the dismiss function of the parent
       *  scope
       */
      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
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
      /**
       * uploaderfunc: the callback function passed to sdUploader. Depending on
       *  the `event_message` from sdUploader, it will change the state of the
       *  modal, show the `invalid_extension` alert, and update the progress bar.
       */
      $scope.uploaderfunc = function (event_message, file, progress) {
        if (event_message === 'invalid_extension') {
          $scope.uploader.invalid_extension_alert = true;
        }
        if (event_message === 'upload_submitted') {
          $scope.dataset.filename = file.filename;
          $scope.uploader.in_progress = true;
          $scope.uploader.status_message = 'uploading file';
        }
        if (event_message === 'upload_complete') {
          var current_step = $scope.step.number;

          $scope.uploader.status_message = 'upload complete';
          $scope.dataset.filename = file.filename;
          $scope.dataset.import_file_id = file.file_id;
          // Assessed Data; upload is step 2; PM import is currently treated as such, and is step 13
          if (current_step === 2 || current_step === 13) {
            var is_green_button = (file.source_type === 'Green Button Raw');
            save_raw_assessed_data(file.file_id, file.cycle_id, is_green_button);
          }
          // Portfolio Data
          if (current_step === 4) {
            save_map_match_PM_data(file.file_id, file.cycle_id);
          }

        }
        if (event_message === 'upload_in_progress') {
          $scope.uploader.in_progress = true;
          $scope.uploader.progress = 25.0 * progress.loaded / progress.total;
        }
        // $apply() or $digest() needed maybe because of this:
        // https://github.com/angular-ui/bootstrap/issues/1798
        // otherwise alert doesn't show unless modal is interacted with
        if (!$scope.$$phase) {
          $scope.$apply();
        }
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

      /**
       * save_raw_assessed_data: saves Assessed data
       *
       * @param {string} file_id: the id of the import file
       * @param cycle_id
       * @param is_green_button
       */
      var save_raw_assessed_data = function (file_id, cycle_id, is_green_button) {
        $scope.uploader.status_message = 'saving data';
        $scope.uploader.progress = 45;
        uploader_service.save_raw_data(file_id, cycle_id).then(function (data) {
          uploader_service.check_progress_loop(data.progress_key, 45, 0.55, function () {
            $scope.uploader.status_message = 'saving complete';
            $scope.uploader.progress = 100;

            if (is_green_button) {
              $scope.step.number = 8;
            } else {
              $scope.step.number = 3;
            }

          }, function (data) {
            $log.error(data.message);
            if (data.hasOwnProperty('stacktrace')) $log.error(data.stacktrace);
            $scope.step_12_error_message = data.message;
            $scope.step.number = 12;
          }, $scope.uploader);
        });
      };

      /**
       * find_matches: finds matches for buildings within an import file
       */
      $scope.find_matches = function () {
        var import_file_id = $scope.dataset.import_file_id;
        matching_service.start_system_matching(
          import_file_id
        ).then(function (data) {
          if (_.includes(['error', 'warning'], data.status)) {
            $scope.uploader.complete = true;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 0;
            $scope.step.number = 10;
            $scope.step_10_style = 'danger';
            $scope.step_10_error_message = data.message;
            $scope.step_10_title = data.message;
          } else {
            uploader_service.check_progress_loop(data.progress_key, 0, 1, function (progress_result) {
              var matching_results = progress_result.data;
              inventory_service.get_matching_results($scope.dataset.import_file_id).then(function (data) {
                $scope.duplicate_property_states = matching_results.duplicate_property_states;
                $scope.duplicate_tax_lot_states = matching_results.duplicate_tax_lot_states;
                $scope.duplicates_of_existing_property_states = matching_results.duplicates_of_existing_property_states;
                $scope.duplicates_of_existing_taxlot_states = matching_results.duplicates_of_existing_taxlot_states;
                $scope.import_file_records = matching_results.import_file_records;

                $scope.matched_properties = data.properties.matched;
                $scope.unmatched_properties = data.properties.unmatched;
                $scope.matched_taxlots = data.tax_lots.matched;
                $scope.unmatched_taxlots = data.tax_lots.unmatched;
                $scope.uploader.complete = true;
                $scope.uploader.in_progress = false;
                $scope.uploader.progress = 0;
                if ($scope.matched_properties + $scope.matched_taxlots > 0) {
                  $scope.step.number = 8;
                } else {
                  $scope.step.number = 10;
                }
              });
            }, function () {
              // Do nothing
            },
              $scope.uploader
            );
          }
        });
      };

      $scope.get_pm_report_template_names = function (pm_username, pm_password) {
        spinner_utility.show();
        $scope.pm_buttons_enabled = false;
        $scope.pm_warning_message = false;
        $http.post('/api/v2_1/portfolio_manager/template_list/', {
          username: pm_username,
          password: pm_password
        }).then(function (response) {
          $scope.pm_error_alert = false;
          if (response.data.any_errors) {
            $scope.pm_warning_message = 'Issues encountered getting templates, but I will keep trying!';
          }
          $scope.pm_templates = response.data.templates; // response.data now also has an 'any_errors' member we could check
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
        $scope.pm_warning_message = false;
        $http.post('/api/v2_1/portfolio_manager/report/', {
          username: pm_username,
          password: pm_password,
          template: pm_template
        }).then(function (response) {
          if (response.data.any_errors) {
            $scope.pm_warning_message = 'Issues encountered generating report, but I will keep trying!';
          }
          response = $http.post('/api/v2/upload/create_from_pm_import/', {
            properties: response.data.properties, // response.data now also has an 'any_errors' member we could check
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
