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
      systems_old,
      systems,
      organization_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.systems = systems.data;
      $scope.systems_old = systems_old.data; // rp - testing

      $scope.open_create_system_modal = () => {
          const modalInstance = $uibModal.open({
            templateUrl: `${urls.static_url}seed/partials/create_system_modal.html`,
            controller: 'create_system_modal_controller',
            resolve: {
              group_id: () => $stateParams.group_id,
              organization_payload: () => organization_payload,
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

      const setSystemGridOptions = () => {
        $scope.gridOptionsBySystemId = {}
        $scope.gridApiBySystemId = {}
        $scope.show_uigrid = {}

        const systems_combined = [...systems.data.DES, ...systems.data.EVSE, ...systems.data.Battery]
        systems_combined.forEach((system) => {
          const systemGridOptions = {
            data: system.services,
            enableColumnMenus: false,
            minRowsToShow: system.services.length,
            flatEntityAccess: true,
            fastWatch: true,
            onRegisterApi(gridApi) {
              $scope.gridApiBySystemId[system.id] = gridApi;
            }
          }
          $scope.gridOptionsBySystemId[system.id] = systemGridOptions;
        })
      }

      // without resizing, ui-grids appear blank
      $scope.collapse = (system_id) => {
        const gridApi = $scope.gridApiBySystemId[system_id];
        gridApi.grid.refresh();
        setTimeout(gridApi.core.handleWindowResize, 50);
      }

      // initialize system ui-grids
      setSystemGridOptions();
    
    }]);
