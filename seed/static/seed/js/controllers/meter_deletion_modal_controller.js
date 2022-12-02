angular.module('BE.seed.controller.meter_deletion_modal', [])
  .controller('meter_deletion_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'meter_service',
    'meter',
    'view_id',
    'refresh_meters_and_readings',
    function (
      $scope,
      $state,
      $uibModalInstance,
      meter_service,
      meter,
      view_id,
      refresh_meters_and_readings,
    ) {
      $scope.meter_name = meter.alias ?? "meter"

      $scope.delete_meter = function () {
        meter_service.delete_meter(view_id, meter.id).then(() => {
          refresh_meters_and_readings();
          $uibModalInstance.dismiss('cancel');
        })
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
      };

    }]);
