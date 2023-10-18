/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.column_mapping_profile_modal', []).controller('column_mapping_profile_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'action',
  'column_mappings_service',
  'data',
  'org_id',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, action, column_mappings_service, data, org_id) {
    $scope.action = action;
    $scope.data = data;
    $scope.org_id = org_id;

    $scope.rename_profile = () => {
      if (!$scope.disabled()) {
        const profile_id = $scope.data.id;
        const updated_data = { name: $scope.newName };
        column_mappings_service.update_column_mapping_profile($scope.org_id, profile_id, updated_data).then((result) => {
          $uibModalInstance.close(result.data.name);
        });
      }
    };

    $scope.remove_profile = () => {
      column_mappings_service.delete_column_mapping_profile($scope.org_id, $scope.data.id).then(() => {
        $uibModalInstance.close();
      });
    };

    $scope.new_profile = () => {
      if (!$scope.disabled()) {
        column_mappings_service
          .new_column_mapping_profile_for_org($scope.org_id, {
            name: $scope.newName,
            mappings: $scope.data.mappings,
            profile_type: $scope.data.profile_type
          })
          .then((result) => {
            $uibModalInstance.close(result.data);
          });
      }
    };

    $scope.disabled = () => {
      if ($scope.action === 'rename') {
        return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
      }
      if ($scope.action === 'new') {
        return _.isEmpty($scope.newName);
      }
      return false;
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
