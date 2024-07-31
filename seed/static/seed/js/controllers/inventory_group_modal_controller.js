/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_modal', [])
  .controller('inventory_group_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'action',
    'inventory_group_service',
    'inventory_type',
    'data',
    'org_id',
    function (
      $scope,
      $uibModalInstance,
      action,
      inventory_group_service,
      inventory_type,
      data,
      org_id
    ) {
      $scope.action = action;
      $scope.data = data;
      $scope.org_id = org_id;
      $scope.inventory_type = inventory_type;

      $scope.rename_inventory_group = function () {
        if (!$scope.disabled()) {
          var id = $scope.data.id;
          var group = _.omit($scope.data, 'id');
          group.name = $scope.newName;
          inventory_group_service.update_group(id, group).then(function (result) {
            $uibModalInstance.close(result.name);
          }).catch(function () {
            $uibModalInstance.dismiss();
          });
        }
      };

      $scope.remove_inventory_group = function () {
        inventory_group_service.remove_group($scope.data.id).then(function () {
          $uibModalInstance.close();
        }).catch(function () {
          $uibModalInstance.dismiss();
        });
      };

      $scope.new_inventory_group = function () {
        if (!$scope.disabled()) {
          inventory_group_service.new_group({
            name: $scope.newName,
            inventory_type: $scope.inventory_type,
            organization: $scope.org_id
          }).then(function (result) {
            $uibModalInstance.close(result.data);
          });
        }
      };

      $scope.disabled = function () {
        if ($scope.action === 'rename') {
          return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
        } else if ($scope.action === 'new') {
          return _.isEmpty($scope.newName);
        }
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
  }]);
