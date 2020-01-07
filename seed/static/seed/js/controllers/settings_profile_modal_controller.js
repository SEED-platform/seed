/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.settings_profile_modal', [])
  .controller('settings_profile_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'inventory_service',
    'action',
    'data',
    'settings_location',
    'inventory_type',
    function ($scope, $uibModalInstance, inventory_service, action, data, settings_location, inventory_type) {
      $scope.action = action;
      $scope.data = data;
      $scope.settings_location = settings_location;
      $scope.inventory_type = inventory_type;

      $scope.rename_profile = function () {
        if (!$scope.disabled()) {
          var id = $scope.data.id;
          var profile = _.omit($scope.data, 'id');
          profile.name = $scope.newName;
          inventory_service.update_settings_profile(id, profile).then(function (result) {
            $uibModalInstance.close(result.name);
          });
        }
      };

      $scope.remove_profile = function () {
        inventory_service.remove_settings_profile($scope.data.id).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.new_profile = function () {
        if (!$scope.disabled()) {
          inventory_service.new_settings_profile({
            name: $scope.newName,
            settings_location: $scope.settings_location,
            inventory_type: $scope.inventory_type,
            columns: $scope.data
          }).then(function (result) {
            result.columns = _.sortBy(result.columns, ['order', 'column_name']);
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
