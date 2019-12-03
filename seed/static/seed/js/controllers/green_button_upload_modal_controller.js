angular.module('BE.seed.controller.green_button_upload_modal', [])
  .controller('green_button_upload_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'uiGridConstants',
    'filler_cycle',
    'dataset_service',
    'meters_service',
    'organization_id',
    'uploader_service',
    'view_id',
    'datasets',
    function (
      $scope,
      $state,
      $uibModalInstance,
      uiGridConstants,
      filler_cycle,
      dataset_service,
      meters_service,
      organization_id,
      uploader_service,
      view_id,
      datasets
    ) {
      $scope.step = {
        number: 1
      };
      $scope.view_id = view_id;
      $scope.selectedCycle = filler_cycle;
      $scope.organization_id = organization_id;
      $scope.datasets = datasets;

      if (datasets.length) $scope.selectedDataset = datasets[0];

      $scope.uploader = {
        invalid_file_contents: false,
        invalid_xml_extension_alert: false,
        progress: 0,
        status_message: ''
      };

      $scope.datasetChanged = function (dataset) {
        // set selectedDataset to null to rerender button
        $scope.selectedDataset = null;
        $scope.selectedDataset = dataset;
      };

      $scope.cancel = function () {
        // If step 2, GB import confirmation was not accepted by user, so delete file
        if ($scope.step.number === 2) {
          dataset_service.delete_file($scope.file_id).then(function (/*results*/) {
            $uibModalInstance.dismiss('cancel');
          });
        } else {
          $uibModalInstance.dismiss('cancel');
        }
      };

      $scope.uploaderfunc = function (event_message, file/*, progress*/) {
        switch (event_message) {
          case 'invalid_extension':
            $scope.$apply(function () {
              $scope.uploader.invalid_xml_extension_alert = true;
              $scope.uploader.invalid_file_contents = false;
            });
            break;

          case 'upload_complete':
            $scope.file_id = file.file_id;
            $scope.filename = file.filename;
            show_confirmation_info();
            break;
        }
      };

      var saveFailure = function (error) {
        // Delete file and present error message

        // file_id source varies depending on which step the error occurs
        var file_id = $scope.file_id || error.config.data.file_id;
        dataset_service.delete_file(file_id);

        $scope.uploader.invalid_xml_extension_alert = false;
        $scope.uploader.invalid_file_contents = true;

        // Be sure user is back to step 1 where the error is shown and they can upload another file
        $scope.step.number = 1;
      };

      var base_green_button_col_defs = [{
        field: 'source_id',
        displayName: 'GreenButton UsagePoint',
        enableHiding: false,
        type: 'string'
      }, {
        field: 'type',
        enableHiding: false
      }, {
        field: 'incoming',
        enableHiding: false
      }];

      var successfully_imported_col_def = {
        field: 'successfully_imported',
        enableHiding: false
      };

      var grid_rows_to_display = function (data) {
        return Math.min(data.length, 5);
      };

      var show_confirmation_info = function () {
        meters_service.greenbutton_parsed_meters_confirmation($scope.file_id, $scope.organization_id, $scope.view_id).then(function (result) {
          $scope.proposed_imports_options = {
            data: result.proposed_imports,
            columnDefs: base_green_button_col_defs,
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
            enableVerticalScrollbar: result.proposed_imports.length <= 5 ? uiGridConstants.scrollbars.NEVER : uiGridConstants.scrollbars.WHEN_NEEDED,
            minRowsToShow: grid_rows_to_display(result.validated_type_units)
          };

          var modal_element = angular.element(document.getElementsByClassName('modal-dialog'));
          modal_element.addClass('modal-lg');

          $scope.step.number = 2;
        }).catch(saveFailure);
      };

      var saveSuccess = function (progress_data) {
        // recheck progress in order to ensure message has been appended to progress_data
        uploader_service.check_progress(progress_data.progress_key).then(function (data) {
          $scope.uploader.status_message = 'saving complete';
          $scope.uploader.progress = 100;
          buildImportResults(data.message);
          $scope.step.number = 4;
        });
      };

      var buildImportResults = function (message) {
        var col_defs = base_green_button_col_defs;

        col_defs.push(successfully_imported_col_def);

        if (_.has(message, '[0].errors')) {
          col_defs.push({
            field: 'errors',
            enableHiding: false
          });
        }

        $scope.import_result_options = {
          data: message,
          columnDefs: col_defs,
          enableColumnResizing: true,
          enableHorizontalScrollbar: uiGridConstants.scrollbars.NEVER,
          enableVerticalScrollbar: message.length <= 5 ? uiGridConstants.scrollbars.NEVER : uiGridConstants.scrollbars.WHEN_NEEDED,
          minRowsToShow: grid_rows_to_display(message)
        };
      };

      $scope.accept_greenbutton_meters = function () {
        uploader_service.save_raw_data($scope.file_id, $scope.selectedCycle).then(function (data) {
          $scope.uploader.status_message = 'saving data';
          $scope.uploader.progress = 0;
          $scope.step.number = 3;

          var progress = _.clamp(data.progress, 0, 100);

          uploader_service.check_progress_loop(
            data.progress_key,
            progress,
            1 - (progress / 100),
            saveSuccess,
            saveFailure, // difficult to reach this as failures should be caught in confirmation step
            $scope.uploader
          );
        });
      };

      $scope.refresh_page = function () {
        $state.reload();
        $uibModalInstance.dismiss('cancel');
      };

    }]);
