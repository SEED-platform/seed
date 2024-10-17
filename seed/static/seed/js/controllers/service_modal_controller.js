/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.service_modal', []).controller('service_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'Notification',
  'service_service',
  'action',
  'group_id',
  'service',
  'system',
  'org_id',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    Notification,
    service_service,
    action,
    group_id,
    service,
    system,
    org_id
  ) {
    // $scope.new_service = {};
    $scope.system = system;
    $scope.service = service;
    $scope.action = action;

    $scope.capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);

    $scope.submitServiceForm = () => {
      if (action === 'create') {
        create_service();
      } else if (action === 'remove') {
        remove_service();
      } else if (action === 'edit') {
        update_service();
      }
    };

    const create_service = () => {
      $scope.service.system_id = system.id;
      service_service.create_service(org_id, group_id, system.id, $scope.service).then(
        () => {
          Notification.primary('Created Service');
          $uibModalInstance.close();
        },
        (response) => {
          const errors = Object.values(response.data)
          Notification.error(`${errors}`);
          $uibModalInstance.dismiss('cancel');
        }
      );
    };

    const update_service = () => {
      $scope.service.system_id = system.id;
      service_service.update_service(org_id, group_id, system.id, $scope.service).then(
        () => {
          Notification.primary('Updated Service');
          $uibModalInstance.close();
        },
        (response) => {
          const errors = Object.values(response.data)
          Notification.error(`${errors}`);
          $uibModalInstance.dismiss('cancel');
        }
      );
    };

    const remove_service = () => {
      service_service.remove_service(org_id, group_id, system.id, service.id).then(
        () => {
          Notification.primary('Removed Service');
          $uibModalInstance.close();
        },
        (response) => {
          Notification.error(`Failed to remove Service: ${response.data.message}`);
          $uibModalInstance.dismiss('cancel');
        }
      );
    };

    $scope.cancel = () => $uibModalInstance.dismiss();
  }
]);
