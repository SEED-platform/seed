/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.system_meter_readings_upload_modal', []).controller('system_meter_readings_upload_modal_controller', [
  '$scope',
  '$stateParams',
  '$uibModalInstance',
  'inventory_group_service',
  'inventory_service',
  'meter_service',
  'uploader_service',
  'spinner_utility',
  'organization',
  'meter',
  'datasets',
  'filler_cycle',
  'refresh_meters_and_readings',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $stateParams,
    $uibModalInstance,
    inventory_group_service,
    inventory_service,
    meter_service,
    uploader_service,
    spinner_utility,
    organization,
    meter,
    datasets,
    filler_cycle,
    refresh_meters_and_readings
  ) {
    $scope.state = 'upload';
    $scope.meter = meter;
    $scope.organization = organization;
    $scope.organization_id = organization.id;
    $scope.datasets = datasets;
    $scope.selectedDataset = datasets[0];
    $scope.selectedCycle = filler_cycle;

    $scope.uploader = {
      invalid_file_contents: false,
      invalid_csv_extension_alert: false,
      invalid_xlsx_extension_alert: false,
      progress: 0,
      status_message: ''
    };

    $scope.uploaderfunc = (event_message, file /* , progress */) => {
      switch (event_message) {
        case 'invalid_extension':
          $scope.$apply(() => {
            $scope.uploader.invalid_csv_extension_alert = true;
            $scope.uploader.invalid_xlsx_extension_alert = true;
            $scope.uploader.invalid_file_contents = false;
          });
          break;

        case 'upload_complete':
          $scope.state = 'processing';
          uploader_service
            .system_meter_upload(file.file_id, $scope.organization.org_id, meter.id)
            .then((data) => {
              $scope.state = 'confirmation';
              $scope.confirmation_message = data.message;
            })
            .catch((err) => {});
          break;
      }
    };

    $scope.dismiss = () => {
      refresh_meters_and_readings();
      spinner_utility.show();
      $uibModalInstance.dismiss('cancel');
    };
  }
]);
