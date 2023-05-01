/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.new_member_modal', [])
  .controller('new_member_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'organization',
    'user_service',
    '$timeout',
    '$translate',
    'access_level_tree',
    'level_names',
    function (
      $scope,
      $uibModalInstance,
      organization,
      user_service,
      $timeout,
      $translate,
      access_level_tree,
      level_names,
    ) {
      $scope.access_level_tree = access_level_tree;
      $scope.level_names = level_names;
      $scope.level_name_index = null;
      $scope.potental_level_instances = [];

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
        new_level_instance_depth = parseInt($scope.level_name_index) + 1
        $scope.potental_level_instances = access_level_instances_by_depth[new_level_instance_depth]
      }

      $scope.roles = [{
        name: $translate.instant('Owner'),
        value: 'owner'
      }, {
        name: $translate.instant('Member'),
        value: 'member'
      }, {
        name: $translate.instant('Viewer'),
        value: 'viewer'
      }];
      $scope.user = {
        organization,
        role: $scope.roles[1]
      };

      /**
       * adds a user to the org
       */
      $scope.submit_form = function () {
        // make `role` a string
        const u = _.cloneDeep($scope.user);
        u.role = u.role.value;

        user_service.add(u).then(function () {
          $uibModalInstance.close();
        }, function (data) {
          $scope.$emit('app_error', data);
        });
      };

      $scope.close = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
      };

      $timeout(function () {
        angular.element('#newMemberFirstName').focus();
      }, 50);
    }]);
