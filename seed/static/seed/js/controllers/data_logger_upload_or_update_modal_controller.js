/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.data_logger_upload_or_update_modal', []).controller('data_logger_upload_or_update_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'data_logger',
  'filler_cycle',
  'organization_id',
  'sensor_service',
  'view_id',
  // eslint-disable-next-line func-names
  function ($scope, $state, $uibModalInstance, data_logger, filler_cycle, organization_id, sensor_service, view_id) {
    $scope.view_id = view_id;
    $scope.selectedCycle = filler_cycle;
    $scope.organization_id = organization_id;
    $scope.data_logger = { ...data_logger } ?? {
      display_name: null,
      location_description: '',
      id: null,
      manufacturer_name: null,
      model_name: null,
      serial_number: null,
      identifier: null
    };

    $scope.create_data_logger = () => {
      // error out if display name is empty
      $scope.data_logger_display_name_not_entered_alert = (
        $scope.data_logger.display_name == null || $scope.data_logger.display_name === ''
      );
      if ($scope.data_logger_display_name_not_entered_alert) { return; }

      if (data_logger === undefined) {
        sensor_service
          .create_data_logger(
            $scope.view_id,
            $scope.organization_id,
            $scope.data_logger.display_name,
            $scope.data_logger.location_description,
            $scope.data_logger.manufacturer_name,
            $scope.data_logger.model_name,
            $scope.data_logger.serial_number,
            $scope.data_logger.identifier
          )
          .then((result) => {
            $scope.data_logger = result;
            $scope.refresh_page();
          })
          .catch((err) => {
            if (err.status === 400) {
              $scope.error_message = format_errors(err.data.errors);
            }
          });
      } else {
        sensor_service
          .update_data_logger(
            $scope.organization_id,
            $scope.data_logger.id,
            $scope.data_logger.display_name,
            $scope.data_logger.location_description,
            $scope.data_logger.manufacturer_name,
            $scope.data_logger.model_name,
            $scope.data_logger.serial_number,
            $scope.data_logger.identifier
          )
          .then((result) => {
            $scope.data_logger = result;
            $scope.refresh_page();
          })
          .catch((err) => {
            if (err.status === 400) {
              $scope.error_message = format_errors(err.data.errors);
            }
          });
      }
    };

    $scope.refresh_page = () => {
      $state.reload();
      $uibModalInstance.dismiss('cancel');
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    const format_errors = (errors) => Object.entries(errors)
      .map(([key, value]) => (key === 'non_field_errors' ? ` ${value.join('. ')}` : ` ${key}: ${value.join('. ')}`))
      .join('. ');
  }
]);
