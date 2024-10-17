/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.system_modal', []).controller('system_modal_controller', [
  '$scope',
  '$state',
  '$timeout',
  '$uibModalInstance',
  'uiGridConstants',
  'Notification',
  'system_service',
  'action',
  'group_id',
  'org_id',
  'system',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $timeout,
    $uibModalInstance,
    uiGridConstants,
    Notification,
    system_service,
    action,
    group_id,
    org_id,
    system
  ) {
    $scope.des_types = ['Boiler', 'Chiller', 'CHP'];
    $scope.evse_types = ['Level1-120V', 'Level2-240V', 'Level3-DC Fast'];
    $scope.action = action;

    $scope.system = system || { type: null };

    $scope.capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);

    $scope.submitSystemForm = () => {
      if (action === 'create') {
        create_system();
      } else if (action === 'remove') {
        remove_system();
      } else if (action === 'edit') {
        update_system();
      }
    };

    const create_system = () => {
      system_service.create_system(org_id, group_id, $scope.system).then(
        () => {
          Notification.primary('Created Sytem');
          $uibModalInstance.close();
        },
        (response) => {
          const errors = Object.values(response.data.errors)
          Notification.error(`${errors}`);
          $uibModalInstance.dismiss('cancel');
        }
      );
    };

    const remove_system = () => {
      system_service.remove_system(org_id, group_id, system.id).then(
        () => {
          Notification.primary(`Deleted System ${system.name}`);
          $uibModalInstance.close();
        },
        (response) => {
          Notification.error(`Failed to delete system: ${response.data.message}`);
          $uibModalInstance.dismiss('cancel');
        }
      );
    };

    const update_system = () => {
      system_service.update_system(org_id, group_id, system)
        .then(
          () => {
            Notification.primary('Updated Sytem');
            $uibModalInstance.close();
          },
          (response) => {
            const errors = Object.values(response.data.errors)
            Notification.error(`${errors}`);
            $uibModalInstance.dismiss('cancel');
          }
        );
    };

    $scope.cancel = () => $uibModalInstance.dismiss();
  }
]);
