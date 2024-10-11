/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_detail_systems', [])
  .controller('inventory_group_detail_systems_controller', [
    '$scope',
    '$state',
    '$stateParams',
    '$uibModal',
    'urls',
    'Notification',
    'systems_old',
    'systems',
    'organization_payload',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      $uibModal,
      urls,
      Notification,
      systems_old,
      systems,
      organization_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.systems = systems.data;
      const all_systems = [...$scope.systems.DES, ...$scope.systems.EVSE, ...$scope.systems.Battery]
      $scope.systems_old = systems_old.data; // rp - testing

      $scope.system_tables = [
        { 
          system_key: 'DES', 
          headers: ['Name', 'DES Type', 'Capacity', 'Count'], 
          fields: ['name', 'des_type', 'capacity', 'count']
        },
        { 
          system_key: 'EVSE', 
          headers: ['Name', 'EVSE Type', 'Power', 'Count'], 
          fields: ['name', 'evse_type', 'power', 'count']
        },
        { 
          system_key: 'Battery', 
          headers: ['Name', 'Efficiency', 'Capacity', 'Voltage'], 
          fields: ['name', 'efficiency', 'capacity', 'voltage']
        }
      ]

      $scope.service_table_config = {headers: ['Name', "Emission Factor"], fields: ['name', 'emission_factor']}

      $scope.create_system = () => {
        $scope.open_system_modal('create', {});
      }

      $scope.remove_system = (system_id) => {
        const system = all_systems.find((s) => s.id === system_id)
        $scope.open_system_modal('remove', system)
      }

      $scope.edit_system = (system_id) => {
        const system = all_systems.find((s) => s.id === system_id)
        $scope.open_system_modal('edit', system)
      }

      $scope.open_system_modal = (action, system) => {
          const modalInstance = $uibModal.open({
            templateUrl: `${urls.static_url}seed/partials/system_modal.html`,
            controller: 'system_modal_controller',
            resolve: {
              action: () => action,
              group_id: () => $stateParams.group_id,
              organization_payload: () => organization_payload,
              system: () => system,
            }
          });

          modalInstance.result.then(() => {
            $state.reload();
          });
      }

      $scope.open_create_service_modal = (system) => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/create_service_modal.html`,
          controller: 'create_service_modal_controller',
          resolve: {
            group_id: () => $stateParams.group_id,
            system: () => system,
            organization_payload: () => organization_payload,
          }
        });

        modalInstance.result.then(() => {
          $state.reload();
        });
      }
    
    }]);
