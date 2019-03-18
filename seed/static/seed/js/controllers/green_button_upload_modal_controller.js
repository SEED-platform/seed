angular.module('BE.seed.controller.green_button_upload_modal', [])
  .controller('green_button_upload_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'filler_cycle',
    'dataset_service',
    'meters_service',
    'organization_id',
    'view_id',
    function (
      $scope,
      $uibModalInstance,
      filler_cycle,
      dataset_service,
      meters_service,
      organization_id,
      view_id
    ) {
      $scope.step = {
        number: 1
      };
      $scope.view_id = view_id;
      $scope.selectedCycle = filler_cycle;
      $scope.organization_id = organization_id;

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
            // TODO: placeholder for showing progress
            break;

          case 'upload_error':
            debugger;
            // TODO: to be revisited
            break;

          case 'upload_in_progress':
            // debugger;
            // TODO: placeholder for showing progress
            break;

          case 'upload_complete':
            show_confirmation_info(file.file_id);
            break;
        }
      };

      var show_confirmation_info = function(file_id) {
        meters_service.greenbutton_parsed_meters_confirmation(file_id, $scope.organization_id, $scope.view_id).then(function(result) {
          $scope.step.number = 2;
        });
      };

    }]);
