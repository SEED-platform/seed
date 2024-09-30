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
    // eslint-disable-next-line func-names
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

      $scope.rename_inventory_group = () => {
        if (!$scope.disabled()) {
          const id = $scope.data.id;
          const group = _.omit($scope.data, 'id');
          group.name = $scope.newName;
          inventory_group_service.update_group(id, group).then((result) => {
            $uibModalInstance.close(result.name);
          }).catch(() => {
            $uibModalInstance.dismiss();
          });
        }
      };

      $scope.remove_inventory_group = () => {
        inventory_group_service.remove_group($scope.data.id).then(() => {
          $uibModalInstance.close();
        }).catch(() => {
          $uibModalInstance.dismiss();
        });
      };

      $scope.new_inventory_group = () => {
        if (!$scope.disabled()) {
          inventory_group_service.new_group({
            name: $scope.newName,
            inventory_type: $scope.inventory_type,
            organization: $scope.org_id,
            access_level_instance: 1 // TODO: add access level instance dropdown to modal
          }).then((result) => {
            $uibModalInstance.close(result.data);
          });
        }
      };

      $scope.disabled = () => {
        if ($scope.action === 'rename') {
          return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
        } if ($scope.action === 'new') {
          return _.isEmpty($scope.newName);
        }
      };

      $scope.cancel = () => {
        $uibModalInstance.dismiss();
      };
    }]);
