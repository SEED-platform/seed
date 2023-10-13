/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.settings_profile_modal', []).controller('settings_profile_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'inventory_service',
  'action',
  'data',
  'profile_location',
  'inventory_type',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, inventory_service, action, data, profile_location, inventory_type) {
    $scope.action = action;
    $scope.data = data;
    $scope.profile_location = profile_location;
    $scope.inventory_type = inventory_type;

    $scope.rename_profile = () => {
      if (!$scope.disabled()) {
        const { id } = $scope.data;
        const profile = _.omit($scope.data, 'id');
        profile.name = $scope.newName;
        inventory_service
          .update_column_list_profile(id, profile)
          .then((result) => {
            $uibModalInstance.close(result.name);
          })
          .catch(() => {
            $uibModalInstance.dismiss();
          });
      }
    };

    $scope.remove_profile = () => {
      inventory_service
        .remove_column_list_profile($scope.data.id)
        .then(() => {
          $uibModalInstance.close();
        })
        .catch(() => {
          $uibModalInstance.dismiss();
        });
    };

    $scope.new_profile = () => {
      if (!$scope.disabled()) {
        inventory_service
          .new_column_list_profile({
            name: $scope.newName,
            profile_location: $scope.profile_location,
            inventory_type: $scope.inventory_type,
            columns: $scope.data.columns,
            derived_columns: $scope.data.derived_columns
          })
          .then((result) => {
            result.columns = _.sortBy(result.columns, ['order', 'column_name']);
            result.derived_columns = _.sortBy(result.derived_columns, ['column_name']);
            $uibModalInstance.close(result);
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
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
