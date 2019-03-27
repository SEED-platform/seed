angular.module('BE.seed.controller.green_button_upload_modal', [])
  .controller('green_button_upload_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'filler_cycle',
    'dataset_service',
    'meters_service',
    'organization_id',
    'uploader_service',
    'view_id',
    function (
      $scope,
      $uibModalInstance,
      filler_cycle,
      dataset_service,
      meters_service,
      organization_id,
      uploader_service,
      view_id
    ) {
      $scope.step = {
        number: 1
      };
      $scope.view_id = view_id;
      $scope.selectedCycle = filler_cycle;
      $scope.organization_id = organization_id;

      $scope.uploader = {
        progress: 0,
        status_message: ''
      };

      dataset_service.get_datasets().then(function(result) {
        $scope.datasets = result.datasets;
      });

      $scope.datasetChanged = function(dataset) {
        // set selectedDataset to null to rerender button
        $scope.selectedDataset = null;
        $scope.selectedDataset = dataset;
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
      };

      $scope.uploaderfunc = function (event_message, file, progress) {
        switch (event_message) {
          case 'invalid_extension':
            debugger;
            // TODO: to be revisited
            break;

          case 'upload_submitted':
            // debugger;
            // TODO: to be revisited
            break;

          case 'upload_error':
            debugger;
            // TODO: to be revisited
            break;

          case 'upload_in_progress':
            // debugger;
            // TODO: to be revisited
            break;

          case 'upload_complete':
            $scope.file_id = file.file_id;
            $scope.filename = file.filename;
            show_confirmation_info();
            break;
        }
      };

      var base_green_button_col_defs = [
        {
          field: "source_id",
          displayName: "GreenButton UsagePoint",
          type: "string",
        },
        {
          field: "incoming",
        },
      ];

      var successfully_imported_col_def = {
          field: "successfully_imported",
      };

      var errors_col_def = {
          field: "errors",
      };

      var show_confirmation_info = function() {
        meters_service.greenbutton_parsed_meters_confirmation($scope.file_id, $scope.organization_id, $scope.view_id).then(function(result) {
          $scope.proposed_imports_options = {
              data: result.proposed_imports,
              columnDefs: base_green_button_col_defs,
          };
          $scope.parsed_type_units = result.validated_type_units;
          $scope.step.number = 2;
        });
      };

      var saveSuccess = function (progress_data) {
        $scope.uploader.status_message = 'saving complete';
        $scope.uploader.progress = 100;
        buildImportResults(progress_data.message);
        $scope.step.number = 4;
      };

      var buildImportResults = function (message) {
        var col_defs = base_green_button_col_defs;

        col_defs.push(successfully_imported_col_def);

        if (message[0].hasOwnProperty("errors")) {
          col_defs.push(errors_col_def);
        }

        $scope.import_results = {
          data: message,
          columnDefs: col_defs,
        };
      };

      var saveFailure = function () {
        // debugger; // TODO: to be revisited
      };

      $scope.accept_greenbutton_meters = function() {
        uploader_service.save_raw_data($scope.file_id, $scope.selectedCycle).then(function(data) {
          $scope.uploader.status_message = 'saving data';
          $scope.uploader.progress = 0;
          $scope.step.number = 3;

          var progress = _.clamp(data.progress, 0, 100);

          uploader_service.check_progress_loop(
            data.progress_key,
            progress,
            1 - (progress / 100),
            saveSuccess,
            saveFailure,
            $scope.uploader
          )
        });
      };

    }]);
