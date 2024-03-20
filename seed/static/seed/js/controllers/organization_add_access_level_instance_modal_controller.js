/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization_add_access_level_instance_modal', [])
  .controller('organization_add_access_level_instance_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'ah_service',
    'organization_service',
    'org_id',
    'level_names',
    'access_level_tree',
    'Notification',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      ah_service,
      organization_service,
      org_id,
      level_names,
      access_level_tree,
      Notification
    ) {
      $scope.level_names = level_names;
      $scope.selected_level_index = null;
      $scope.parent = null;
      $scope.potential_parents = [];
      $scope.new_level_instance_name = '';

      const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth(access_level_tree);

      $scope.change_selected_level_index = () => {
        const new_level_instance_depth = parseInt($scope.selected_level_index, 10);
        $scope.potential_parents = access_level_instances_by_depth[new_level_instance_depth];
        $scope.parent = null;
      };

      // attempt to default the access level
      if ($scope.level_names.length > 1) {
        $scope.selected_level_index = 1;
        $scope.change_selected_level_index();
      }

      $scope.create_new_level_instance = () => {
        organization_service.create_organization_access_level_instance(org_id, $scope.parent.id, $scope.new_level_instance_name)
          .then(() => $uibModalInstance.close())
          .catch((err) => { Notification.error(err); });
      };

      $scope.cancel = () => {
        $uibModalInstance.dismiss('cancel');
      };
    }]);
