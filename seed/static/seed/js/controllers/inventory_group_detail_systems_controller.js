/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_detail_systems', [])
  .controller('inventory_group_detail_systems_controller', [
    '$scope',
    '$state',
    '$stateParams',
    '$timeout',
    '$uibModal',
    'urls',
    'dataset_service',
    'cycles',
    'systems',
    'organization_payload',
    'group',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      $timeout,
      $uibModal,
      urls,
      dataset_service,
      cycles,
      systems,
      organization_payload,
      group
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.inventory_display_name = group.name;
      $scope.systems = systems.data;
      const system_types = ['DES - Cooling', 'DES - Heating', 'EVSE', 'Battery'];
      const all_systems = system_types.flatMap((type) => $scope.systems[type] ?? []);
      const org_id = organization_payload.organization.id;
      $scope.filler_cycle = cycles.cycles[0].id;

      $scope.system_tables = [
        {
          system_key: 'DES - Cooling',
          headers: ['Name', 'DES Type', 'Capacity (Ton)', 'Count'],
          fields: ['name', 'des_type', 'cooling_capacity', 'count']
        },
        {
          system_key: 'DES - Heating',
          headers: ['Name', 'DES Type', 'Capacity (MMBtu)', 'Count'],
          fields: ['name', 'des_type', 'heating_capacity', 'count']
        },
        {
          system_key: 'EVSE',
          headers: ['Name', 'EVSE Type', 'Power (kW)', 'Voltage (V)', 'Count'],
          fields: ['name', 'evse_type', 'power', 'voltage', 'count']
        },
        {
          system_key: 'Battery',
          headers: ['Name', 'Efficiency (%)', 'Energy Capacity (kWh)', 'Power Capacity (kW)', 'Voltage (V)'],
          fields: ['name', 'efficiency', 'energy_capacity', 'power_capacity', 'voltage']
        }
      ];

      $scope.service_table_config = { headers: ['Name', 'Emission Factor'], fields: ['name', 'emission_factor'] };

      $scope.create_system = () => {
        $scope.open_system_modal('create', {});
      };

      $scope.remove_system = (system_id) => {
        const system = all_systems.find((s) => s.id === system_id);
        $scope.open_system_modal('remove', system);
      };

      $scope.edit_system = (system_id) => {
        const system = all_systems.find((s) => s.id === system_id);
        $scope.open_system_modal('edit', system);
      };

      $scope.open_system_modal = (action, system) => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/system_modal.html`,
          controller: 'system_modal_controller',
          resolve: {
            action: () => action,
            group_id: () => $stateParams.group_id,
            org_id: () => org_id,
            system: () => system
          }
        });

        modalInstance.result.finally(() => {
          $state.reload();
        });
      };

      $scope.create_service = (system_id) => {
        const system = all_systems.find((s) => s.id === system_id);
        $scope.open_service_modal('create', system, {});
      };

      $scope.edit_service = (system_id, service_id) => {
        const system = all_systems.find((s) => s.id === system_id);
        const service = system.services.find((s) => s.id === service_id);
        $scope.open_service_modal('edit', system, service);
      };

      $scope.remove_service = (system_id, service_id) => {
        const system = all_systems.find((s) => s.id === system_id);
        const service = system.services.find((s) => s.id === service_id);
        $scope.open_service_modal('remove', system, service);
      };

      $scope.open_service_modal = (action, system, service) => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/service_modal.html`,
          controller: 'service_modal_controller',
          resolve: {
            action: () => action,
            group_id: () => $stateParams.group_id,
            service: () => service,
            system: () => system,
            org_id: () => org_id
          }
        });

        modalInstance.result.then(
          () => {
            $state.reload().then(() => {
              $timeout(() => {
                expand_service(system);
              }, 0);
            });
          },
          () => {
            console.log('here');
          // do nothing
          }
        );
      };

      const expand_service = (system) => {
        const element = document.getElementById(`collapse-services-${system.id}`);
        if (element) {
          $(element).collapse('show');
        }
      };
    }]);
