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
    'dataset_service',
    'cycles',
    'systems',
    'organization_payload',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      $uibModal,
      urls,
      dataset_service,
      cycles,
      systems,
      organization_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.systems = systems.data;
      $scope.filler_cycle = cycles.cycles[0].id;

      $scope.open_create_system_modal = () => $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/create_system_modal.html`,
        controller: 'create_system_modal_controller',
        resolve: {
          group_id: () => $stateParams.group_id,
          organization_payload: () => organization_payload,
        }
      });

      $scope.open_create_service_modal = (system) => $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/create_service_modal.html`,
        controller: 'create_service_modal_controller',
        resolve: {
          group_id: () => $stateParams.group_id,
          system: () => system,
          organization_payload: () => organization_payload,
        }
      });

      $scope.open_green_button_upload_modal = (system) => {
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/green_button_upload_modal.html`,
          controller: 'green_button_upload_modal_controller',
          resolve: {
            filler_cycle: () => $scope.filler_cycle,
            organization_id: () => organization_payload.organization.id,
            view_id: () => null,
            system_id: () => system.id,
            datasets: () => dataset_service.get_datasets().then((result) => result.datasets)
          }
        });
      };
    }]);
