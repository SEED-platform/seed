/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.create_system_modal', []).controller('create_system_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'uiGridConstants',
  'Notification',
  'system_service',
  'group_id',
  'organization_payload',
  // eslint-disable-next-line func-names
  function ($scope, $state, $uibModalInstance, uiGridConstants, Notification, system_service, group_id, organization_payload) {
    $scope.DES_types = ["Boiler", "Chiller", "CHP"];
    $scope.EVSE_types = ["Level1-120V", "Level2-240V", "Level3-DC Fast"];

    $scope.new_system = { "type": null };

    $scope.initializeSystem = () => { }

    $scope.submitNewSystemForm = () => {
      console.log($scope.new_system)
      system_service.create_system(organization_payload.organization.id, group_id, $scope.new_system).then(
        (data) => {
          $scope.waiting_for_server = false;
          Notification.primary('Created Analysis');
          $uibModalInstance.close();
        },
        (response) => {
          $scope.waiting_for_server = false;
          $log.error('Error creating new analysis:', response);
          Notification.error(`Failed to create Analysis: ${response.data.message}`);
          $uibModalInstance.dismiss('cancel');
        }
      );
    }

    $scope.cancel = () => $uibModalInstance.dismiss();

  }
]);
