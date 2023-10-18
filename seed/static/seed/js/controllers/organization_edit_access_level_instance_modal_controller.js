/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization_edit_access_level_instance_modal', [])
  .controller('organization_edit_access_level_instance_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'organization_service',
    'org_id',
    'instance_id',
    'instance_name',
    'Notification',
    function (
      $scope,
      $state,
      $uibModalInstance,
      organization_service,
      org_id,
      instance_id,
      instance_name,
      Notification
    ) {
      $scope.instance_id = instance_id;
      $scope.level_instance_name = instance_name;

      $scope.edit_level_instance = function () {
        organization_service.edit_organization_access_level_instance(org_id, $scope.instance_id, $scope.level_instance_name)
          .then((_) => $uibModalInstance.close())
          .catch((err) => { Notification.error(err); });
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
      };
    }]);
