/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_cycle_modal', [])
  .controller('delete_cycle_modal_controller', [
    '$scope',
    '$window',
    '$state',
    '$q',
    '$uibModalInstance',
    'inventory_service',
    'user_service',
    'cycle_service',
    'cycle_id',
    'cycle_name',
    'organization_id',
    function ($scope, $window, $state, $q, $uibModalInstance, inventory_service, user_service, cycle_service, cycle_id, cycle_name, organization_id) {
      $scope.cycle_id = cycle_id;
      $scope.cycle_name = cycle_name;
      $scope.organization_id = organization_id;

      $scope.cycle_has_properties = null;
      $scope.cycle_has_taxlots = null;
      $scope.cycle_has_inventory = null;
      $scope.delete_cycle_status = null;
      $scope.error_occurred = false;

      // determine if there are any properties or tax lots in the cycle
      // when fetching inventory, ask for only 1 inventory per page and first page to reduce overhead
      $q.all([
        inventory_service.get_properties(1, 1, {id: $scope.cycle_id}, null, null, false, $scope.organization_id),
        inventory_service.get_taxlots(1, 1, {id: $scope.cycle_id}, null, null, false, $scope.organization_id)
      ]).then(function (responses) {
        $scope.cycle_has_properties = responses[0].results.length > 0;
        $scope.cycle_has_taxlots = responses[1].results.length > 0;
        $scope.cycle_has_inventory = $scope.cycle_has_properties || $scope.cycle_has_taxlots;
      });

      // open an inventory list page in a new tab
      $scope.goToInventoryList = function (inventory_type) {
        user_service.set_organization(
          { id: organization_id }
        ).then(function (response) {
          inventory_service.save_last_cycle($scope.cycle_id);
          const inventory_url = $state.href('inventory_list', {inventory_type: inventory_type});
          $window.open(inventory_url, '_blank');
          // refresh the current page b/c we have modified the default organization
          location.reload();
        }).catch(function (response) {
          console.error('Failed to set default org: ');
          console.error(response);
          $scope.error_occurred = true;
        })
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };

      // user confirmed deletion of cycle
      $scope.confirmDelete = function () {
        $scope.delete_cycle_status = 'pending';
        cycle_service.delete_cycle($scope.cycle_id, $scope.organization_id)
          .then(function () {
            $scope.delete_cycle_status = 'success';
          })
          .catch(function (res) {
            console.error('Failed to delete cycle: ');
            console.error(res);
            $scope.delete_cycle_status = 'failed';
            $scope.error_occurred = true;
          });
      };
    }]);
