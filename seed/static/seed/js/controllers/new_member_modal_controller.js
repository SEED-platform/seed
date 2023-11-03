/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.new_member_modal', []).controller('new_member_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'organization',
  'user_service',
  '$timeout',
  '$translate',
  'access_level_tree',
  'level_names',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, organization, user_service, $timeout, $translate, access_level_tree, level_names) {
    $scope.access_level_tree = access_level_tree;
    $scope.level_names = level_names;
    $scope.level_name_index = null;
    $scope.potential_level_instances = [];
    $scope.error_message = null;

    /* Build out access_level_instances_by_depth recursively */
    const access_level_instances_by_depth = {};
    const calculate_access_level_instances_by_depth = (tree, depth = 1) => {
      if (tree === undefined) return;
      if (access_level_instances_by_depth[depth] === undefined) access_level_instances_by_depth[depth] = [];
      for (const ali of tree) {
        access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name });
        calculate_access_level_instances_by_depth(ali.children, depth + 1);
      }
    };
    calculate_access_level_instances_by_depth(access_level_tree, 1);

    $scope.change_selected_level_index = () => {
      const new_level_instance_depth = parseInt($scope.level_name_index, 10) + 1;
      $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
    };

    $scope.roles = [
      {
        name: $translate.instant('Owner'),
        value: 'owner'
      },
      {
        name: $translate.instant('Member'),
        value: 'member'
      },
      {
        name: $translate.instant('Viewer'),
        value: 'viewer'
      }
    ];
    $scope.user = {
      organization,
      role: $scope.roles[1].value
    };

    /**
     * adds a user to the org
     */
    $scope.submit_form = () => {
      // make `role` a string
      const u = _.cloneDeep($scope.user);

      user_service.add(u).then(
        () => {
          $uibModalInstance.close();
        },
        (data) => {
          $scope.$emit('app_error', data);
          $scope.error_message = data.data.message;
        }
      );
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    $timeout(() => {
      angular.element('#newMemberFirstName').focus();
    }, 50);
  }
]);
