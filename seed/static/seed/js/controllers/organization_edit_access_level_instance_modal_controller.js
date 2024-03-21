/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
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
    // eslint-disable-next-line func-names
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

      $scope.save_if_changed = () => {
        if (instance_name === $scope.level_instance_name) $scope.cancel();

        organization_service.edit_organization_access_level_instance(org_id, $scope.instance_id, $scope.level_instance_name)
          .then(() => $uibModalInstance.close())
          .catch((err) => { Notification.error(err); });
      };

      $scope.cancel = () => {
        $uibModalInstance.dismiss('cancel');
      };
    }]);
