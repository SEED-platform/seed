/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.move_inventory_modal', []).controller('move_inventory_modal_controller', [
  '$http',
  '$scope',
  '$state',
  '$uibModalInstance',
  'user_service',
  'organization_service',
  'ah_service',
  'ids',
  'org_id',
  'inventory_service',
  // eslint-disable-next-line func-names
  function ($http, $scope, $state, $uibModalInstance, user_service, organization_service, ah_service, ids, org_id, inventory_service) {
    $scope.ids = ids;
    $scope.org_id = org_id;
    let access_level_instances_by_depth = {};
    $scope.label = 'property';
    if (ids.length > 1) {
      $scope.label = 'properties';
    }
    $scope.level_name_index = null;
    $scope.potential_level_instances = [];
    $scope.error_message = null;
    $scope.new_access_level_instance_id = null;
    $scope.moving = false;

    function path_to_string(path) {
      const orderedPath = [];
      for (const i in $scope.level_names) {
        if (Object.prototype.hasOwnProperty.call(path, $scope.level_names[i])) {
          orderedPath.push(path[$scope.level_names[i]]);
        }
      }
      return orderedPath.join(' : ');
    }

    $scope.change_selected_level_index = () => {
      const new_level_instance_depth = parseInt($scope.level_name_index, 10) + 1;
      $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
      for (const key in $scope.potential_level_instances) {
        $scope.potential_level_instances[key].name = path_to_string($scope.potential_level_instances[key].path);
      }
      $scope.potential_level_instances.sort((a, b) => a.name.localeCompare(b.name));
    };
    organization_service.get_organization_access_level_tree(org_id).then((access_level_tree) => {
      $scope.level_names = access_level_tree.access_level_names;
      access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth(access_level_tree.access_level_tree);
    });
    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };

    $scope.move_properties = () => {
      $scope.moving = true;
      inventory_service
        .move_properties($scope.new_access_level_instance_id, $scope.ids)
        .then((result) => {
          $uibModalInstance.close(result);
        })
        .catch((result) => {
          Notification.error({ message: `Error ${result.data.message}`, delay: 15000, closeOnClick: true });
          $uibModalInstance.dismiss('cancel');
        });
      $scope.moving = false;
    };
  }
]);
