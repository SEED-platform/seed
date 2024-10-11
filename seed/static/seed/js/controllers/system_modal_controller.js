/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.system_modal', []).controller('system_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'uiGridConstants',
  'Notification',
  'system_service',
  'action',
  'group_id',
  'organization_payload',
  'system',
  // eslint-disable-next-line func-names
  function (
    $scope, 
    $state, 
    $uibModalInstance, 
    uiGridConstants,
    Notification, 
    system_service, 
    action,
    group_id, 
    organization_payload,
    system,
    ) {
    $scope.des_types = ["Boiler", "Chiller", "CHP"];
    $scope.evse_types = ["Level1-120V", "Level2-240V", "Level3-DC Fast"];
    $scope.action = action;
    const org = organization_payload.organization
    console.log('action', action)


    $scope.system = system ? system : {type: null}

    $scope.capitalize = (str) => {
      return str.charAt(0).toUpperCase() + str.slice(1);
    }

    $scope.submitSystemForm = () => {
      if (action === 'create') {
        create_system()
      } else if (action === 'remove') {
        remove_system()
      }
     
    }

    // document.addEventListener('keypress', function (event) {
    //   if (event.key === 'Enter') {
    //     event.preventDefault()
    //     console.log('enter')
    //     $scope.submitSystemForm()
    //   }
    // });

    const create_system = () => {
      system_service.create_system(organization_payload.organization.id, group_id, $scope.system).then(
        (data) => {
          $scope.waiting_for_server = false;
          Notification.primary('Created Sytem');
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

    const remove_system = () => {
      system_service.remove_system(org.id, group_id, system.id).then(
        () => {
          $scope.waiting_for_server = false;
          Notification.primary(`Deleted System ${system.name}`);
          $uibModalInstance.close();
        },
        (response) => {
          $scope.waiting_for_server = false;
          $log.error('Error deleting system:', response);
          Notification.error(`Failed to delete system: ${response.data.message}`);
          $uibModalInstance.dismiss('cancel');
        }
      );
    }

    $scope.cancel = () => $uibModalInstance.dismiss();

  }
]);
