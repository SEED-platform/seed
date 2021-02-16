/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
    'cycle_service',
    'cycle_id',
    'cycle_name',
    function ($scope, $window, $state, $q, $uibModalInstance, inventory_service, cycle_service, cycle_id, cycle_name) {
      $scope.cycle_id = cycle_id;
      $scope.cycle_name = cycle_name;

      $scope.cycle_has_properties = null;
      $scope.cycle_has_taxlots = null;
      $scope.cycle_has_inventory = null;
      $scope.delete_cycle_success = null;

      // determine if there are any properties or tax lots in the cycle
      // when fetching inventory, to reduce overhead ask for only 1 inventory per page and first page
      $q.all([
        inventory_service.get_properties(1, 1, {id: $scope.cycle_id}, null, null, false),
        inventory_service.get_taxlots(1, 1, {id: $scope.cycle_id}, null, null, false)
      ]).then(function(responses) {
        $scope.cycle_has_properties = responses[0].results.length > 0;
        $scope.cycle_has_taxlots = responses[1].results.length > 0;
        $scope.cycle_has_inventory = $scope.cycle_has_properties || $scope.cycle_has_taxlots;
      });

      // open an inventory list page in a new tab
      $scope.goToInventoryList = function(inventory_type) {
        inventory_service.save_last_cycle($scope.cycle_id);
        const inventory_url = $state.href('inventory_list', {inventory_type: inventory_type});
        $window.open(inventory_url,'_blank');
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };

      // user confirmed deletion of cycle
      $scope.confirmDelete = function () {
        cycle_service.delete_cycle($scope.cycle_id)
          .then(function(res) {
            $scope.delete_cycle_success = true;
          })
          .catch(function(res) {
            console.error('Failed to delete cycle: ')
            console.error(res)
            $scope.delete_cycle_success = false;
          })
      };
    }]);
