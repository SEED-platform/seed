/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_modal', [])
  .controller('inventory_group_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'ah_service',
    'inventory_group_service',
    'user_service',
    'access_level_tree',
    'action',
    'data',
    'inventory_type',
    'org_id',
    function (
      $scope,
      $uibModalInstance,
      ah_service,
      inventory_group_service,
      user_service,
      access_level_tree,
      action,
      data,
      inventory_type,
      org_id
    ) {
      $scope.action = action;
      $scope.data = data;
      $scope.org_id = org_id;
      $scope.inventory_type = inventory_type;
      const access_level_instance = user_service.get_access_level_instance()
      $scope.access_level_tree = access_level_tree.access_level_tree;
      $scope.level_names = access_level_tree.access_level_names.map((level, i) => ({
        index: i,
        name: level
      }));
      $scope.access_level = {};

      const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);
      // $scope.level_name_index = null;
      $scope.change_selected_level_index = () => {
        const new_level_instance_depth = parseInt($scope.access_level.level_name_index, 10) + 1;
        $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
      };

      $scope.edit_inventory_group = function () {
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

      $scope.remove_inventory_group = function () {
        inventory_group_service.remove_group($scope.data.id).then(() => {
          $uibModalInstance.close();
        }).catch(() => {
          $uibModalInstance.dismiss();
        });
      };

      $scope.create_inventory_group = function () {
        if (!$scope.disabled()) {
          inventory_group_service.new_group({
            name: $scope.newName,
            inventory_type: $scope.inventory_type,
            organization: $scope.org_id,
            access_level_instance: $scope.access_level.access_level_instance
          }).then((result) => {
            $uibModalInstance.close(result.data);
          });
        }
      };

      $scope.disabled = function () {
        if ($scope.action === 'edit') {
          return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
        } if ($scope.action === 'create') {

          return (
            _.isEmpty($scope.newName) &&
            _.isEmpty($scope.access_level.access_level_instance)
          )
        }
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
