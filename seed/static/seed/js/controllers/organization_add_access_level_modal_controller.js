/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization_add_access_level_modal', [])
  .controller('organization_add_access_level_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'organization_service',
    'org_id',
    'current_access_level_names',
    'access_level_tree',
    'Notification',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      organization_service,
      org_id,
      current_access_level_names,
      access_level_tree,
      Notification
    ) {
      $scope.new_access_level_names = angular.copy(current_access_level_names);
      $scope.is_modified = () => !_.isEqual(current_access_level_names, $scope.new_access_level_names);
      $scope.num_alis_to_delete = 0;
      $scope.enable_save = true;

      /*
      Build out access_level_instances_by_depth recursively
      We need this to tell how many alis deleting a level would delete
      */
      const access_level_instances_by_depth = {};
      const calculate_access_level_instances_by_depth = function (tree, depth = 1) {
        if (tree == undefined) return;
        if (access_level_instances_by_depth[depth] == undefined) access_level_instances_by_depth[depth] = [];
        tree.forEach((ali) => {
          access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name });
          calculate_access_level_instances_by_depth(ali.children, depth + 1);
        });
      };

      const get_num_alis_at_depth = function(depth) {
        if (Object.keys(access_level_instances_by_depth).length === 0){
          calculate_access_level_instances_by_depth(access_level_tree, 1);
        }
        return access_level_instances_by_depth[depth]?.length ?? 0
      }

      // A deleted level may mean deleting part of the tree itself
      check_for_deletions = () => {
        // if no levels are being deleted, no warning
        $scope.enable_save = true;
        num_levels_to_delete = current_access_level_names.length - $scope.new_access_level_names.length;
        if (num_levels_to_delete <= 0 ) {
          return
        }

        // Get num alis that will be deleted
        depths_to_delete = _.range(current_access_level_names.length-num_levels_to_delete+1, current_access_level_names.length+1)
        $scope.num_alis_to_delete = depths_to_delete.reduce((acc, curr) => acc + get_num_alis_at_depth(curr), 0)

        // if no alis are being deleted, no warning
        if ($scope.num_alis_to_delete > 0){
          $scope.enable_save = false;
        }
      };

      $scope.save_access_level_names = () => {
        organization_service.update_organization_access_level_names(org_id, $scope.new_access_level_names)
          .then(() => $uibModalInstance.close())
          .catch((err) => {
            console.log(err.data.message);
            Notification.error(err.data.message);
          });
      };

      $scope.remove_level = () => {
        $scope.new_access_level_names.pop();
        check_for_deletions();
      };

      $scope.add_level = () => {
        $scope.new_access_level_names.push('');
        check_for_deletions();
      };

      $scope.cancel = () => {
        $uibModalInstance.dismiss('cancel');
      };
    }]);
