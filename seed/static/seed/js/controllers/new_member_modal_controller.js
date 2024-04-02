/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.new_member_modal', []).controller('new_member_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'organization',
  'ah_service',
  'user_service',
  '$timeout',
  '$translate',
  'access_level_tree',
  'level_names',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, organization, ah_service, user_service, $timeout, $translate, access_level_tree, level_names) {
    $scope.access_level_tree = access_level_tree;
    $scope.level_names = level_names;
    $scope.level_name_index = null;
    $scope.potential_level_instances = [];
    $scope.error_message = null;

    const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth(access_level_tree);

    $scope.change_selected_level_index = () => {
      const new_level_instance_depth = parseInt($scope.level_name_index, 10) + 1;
      $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
    };

    OWNER = {
      name: $translate.instant('Owner'),
      value: 'owner'
    }
    MEMBER = {
      name: $translate.instant('Member'),
      value: 'member'
    }
    VIEWER = {
      name: $translate.instant('Viewer'),
      value: 'viewer'
    }
    $scope.get_roles = () => {
      const level_instance_depth = parseInt($scope.level_name_index, 10) + 1;
      if(level_instance_depth == 1){
        return [OWNER, MEMBER, VIEWER]
      } else{
        return [MEMBER, VIEWER]
      }
    }

    $scope.user = {
      organization,
      role: MEMBER
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
