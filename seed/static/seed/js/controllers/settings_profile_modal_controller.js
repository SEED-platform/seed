/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.settings_profile_modal', [])
  .controller('settings_profile_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'inventory_service',
    'action',
    'data',
    'profile_location',
    'inventory_type',
    function ($scope, $uibModalInstance, inventory_service, action, data, profile_location, inventory_type) {
      $scope.action = action;
      $scope.data = data;
      $scope.profile_location = profile_location;
      $scope.inventory_type = inventory_type;

      $scope.rename_profile = function () {
        if (!$scope.disabled()) {
          var id = $scope.data.id;
          var profile = _.omit($scope.data, 'id');
          profile.name = $scope.newName;
          inventory_service.update_column_list_profile(id, profile).then(function (result) {
            $uibModalInstance.close(result.name);
          }).catch(function () {
            $uibModalInstance.dismiss();
          });
        }
      };

      $scope.remove_profile = function () {
        inventory_service.remove_column_list_profile($scope.data.id).then(function () {
          $uibModalInstance.close();
        }).catch(function () {
          $uibModalInstance.dismiss();
        });
      };

      $scope.new_profile = function () {
        if (!$scope.disabled()) {
          inventory_service.new_column_list_profile({
            name: $scope.newName,
            profile_location: $scope.profile_location,
            inventory_type: $scope.inventory_type,
            columns: $scope.data.columns,
            derived_columns: $scope.data.derived_columns
          }).then(function (result) {
            result.columns = _.sortBy(result.columns, ['order', 'column_name']);
            result.derived_columns = _.sortBy(result.derived_columns, ['column_name']);
            $uibModalInstance.close(result);
          });
        }
      };

      $scope.disabled = function () {
        if ($scope.action === 'rename') {
          return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
        } else if ($scope.action === 'new') {
          return _.isEmpty($scope.newName);
        }
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
