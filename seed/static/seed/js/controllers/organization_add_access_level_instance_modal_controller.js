/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization_add_access_level_instance_modal', [])
  .controller('organization_add_access_level_instance_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'organization_service',
    'org_id',
    'level_names',
    'access_level_tree',
    'Notification',
    function (
      $scope,
      $state,
      $uibModalInstance,
      organization_service,
      org_id,
      level_names,
      access_level_tree,
      Notification,
    ) {
      $scope.level_names = level_names;
      $scope.selected_level_index = null;
      $scope.parent = null;
      $scope.potental_parents = [];
      $scope.new_level_instance_name = "";

      /* Build out access_level_instances_by_depth recurrsively */
      access_level_instances_by_depth = {};
      calcuate_access_level_instances_by_depth = function(tree, depth=1){
        if (tree == undefined) return;
        if (access_level_instances_by_depth[depth] == undefined) access_level_instances_by_depth[depth] = [];
        tree.forEach(ali => {
          access_level_instances_by_depth[depth].push({id: ali.id, name: ali.data.name})
          calcuate_access_level_instances_by_depth(ali.children, depth+1);
        })
      }
      calcuate_access_level_instances_by_depth(access_level_tree, 1);

      $scope.change_selected_level_index = function(){
        new_level_instance_depth = parseInt($scope.selected_level_index)
        $scope.potental_parents = access_level_instances_by_depth[new_level_instance_depth]
        $scope.parent = null;
      }

      $scope.create_new_level_instance = function(){
        organization_service.create_organization_access_level_instance(org_id, $scope.parent.id, $scope.new_level_instance_name)
        .then(_ => $uibModalInstance.close())
        .catch(err => {Notification.error(err)});
      }
    }]);