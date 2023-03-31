/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.column_mapping_profile_modal', [])
  .controller('column_mapping_profile_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'action',
    'column_mappings_service',
    'data',
    'org_id',
    function ($scope, $uibModalInstance, action, column_mappings_service, data, org_id) {
      $scope.action = action;
      $scope.data = data;
      $scope.org_id = org_id;

      $scope.rename_profile = function () {
        if (!$scope.disabled()) {
          var profile_id = $scope.data.id;
          var updated_data = {name: $scope.newName};
          column_mappings_service.update_column_mapping_profile($scope.org_id, profile_id, updated_data).then(function (result) {
            $uibModalInstance.close(result.data.name);
          });
        }
      };

      $scope.remove_profile = function () {
        column_mappings_service.delete_column_mapping_profile($scope.org_id, $scope.data.id).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.new_profile = function () {
        if (!$scope.disabled()) {
          column_mappings_service.new_column_mapping_profile_for_org($scope.org_id, {
            name: $scope.newName,
            mappings: $scope.data.mappings,
            profile_type: $scope.data.profile_type
          }).then(function (result) {
            $uibModalInstance.close(result.data);
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
