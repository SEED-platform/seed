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
    'systems',
    'organization_payload',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      $uibModal,
      urls,
      systems,
      organization_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.systems = systems.data;

      $scope.open_create_system_modal = () => $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/create_system_modal.html`,
        controller: 'create_system_modal_controller',
        resolve: {
          group_id: () => $stateParams.group_id,
          organization_payload: () => organization_payload,
        }
      });
    }]);
