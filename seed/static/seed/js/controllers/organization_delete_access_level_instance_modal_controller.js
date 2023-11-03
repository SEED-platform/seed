/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization_delete_access_level_instance_modal', [])
  .controller('organization_delete_access_level_instance_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'organization_service',
    'org_id',
    'instance_id',
    'instance_name',
    'spinner_utility',
    'Notification',
    function (
      $scope,
      $state,
      $uibModalInstance,
      organization_service,
      org_id,
      instance_id,
      instance_name,
      spinner_utility,
      Notification,
    ) {
      $scope.instance_id = instance_id;
      $scope.level_instance_name = instance_name;
      $scope.can_delete_access_level_instance = undefined;
      $scope.reasons_why = [];

      spinner_utility.show();;
      organization_service.can_delete_access_level_instance(org_id, $scope.instance_id)
        .then(res => {
          $scope.can_delete_access_level_instance = res.can_delete;
          if (!$scope.can_delete_access_level_instance) {
            $scope.reasons_why = res.reasons;
          }
        })
        .catch(err => {Notification.error(err)})
        .finally(() => spinner_utility.hide());


      $scope.delete = () => {
        organization_service.delete_access_level_instance(org_id, $scope.instance_id)
        .then(_ => $uibModalInstance.close())
        .catch(err => {Notification.error(err)});
      }
    }]);
