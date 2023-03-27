/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.data_logger_upload_modal', [])
  .controller('data_logger_upload_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'filler_cycle',
    'organization_id',
    'sensor_service',
    'view_id',
    function (
      $scope,
      $state,
      $uibModalInstance,
      filler_cycle,
      organization_id,
      sensor_service,
      view_id,
    ) {
      $scope.view_id = view_id;
      $scope.selectedCycle = filler_cycle;
      $scope.organization_id = organization_id;
      $scope.data_logger = {
          display_name: null,
          location_description: "",
          id: null,
          manufacturer_name: null,
          model_name: null,
          serial_number: null,
          identifier: null,
      };

      $scope.create_data_logger = function(){
        if ($scope.data_logger.display_name == null || $scope.data_logger.display_name == ""){
          $scope.data_logger_display_name_not_entered_alert = true
        }
        else {
          $scope.data_logger_display_name_not_entered_alert = false

          sensor_service.create_data_logger(
            $scope.view_id,
            $scope.organization_id,
            $scope.data_logger.display_name,
            $scope.data_logger.location_description,
            $scope.data_logger.manufacturer_name,
            $scope.data_logger.model_name,
            $scope.data_logger.serial_number,
            $scope.data_logger.identifier,
          ).then((result) => {
            $scope.data_logger = result;
            $scope.refresh_page();
          })
          .catch((err) => {
            if(err.status == 400){
              $scope.data_logger_display_name_not_unique_alert = true
            }
          })
        }
      }

      $scope.refresh_page = function () {
        $state.reload();
        $uibModalInstance.dismiss('cancel');
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
      };

    }]);
