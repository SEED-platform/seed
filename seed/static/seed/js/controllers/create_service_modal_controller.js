/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.create_service_modal', []).controller('create_service_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'uiGridConstants',
  'Notification',
  'system_service',
  'group_id',
  'system',
  'organization_payload',
  // eslint-disable-next-line func-names
  function ($scope, $state, $uibModalInstance, uiGridConstants, Notification, system_service, group_id, system, organization_payload) {
    $scope.new_service = {};

    $scope.initializeService = () => { }

    $scope.submitNewServiceForm = () => {
      console.log($scope.new_service)
      system_service.create_service(organization_payload.organization.id, group_id, system.id, $scope.new_service).then(
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
