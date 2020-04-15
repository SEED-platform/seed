/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.column_mapping_preset_modal', [])
  .controller('column_mapping_preset_modal_controller', [
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

      $scope.rename_preset = function () {
        if (!$scope.disabled()) {
          var preset_id = $scope.data.id;
          var updated_data = {name: $scope.newName}
          column_mappings_service.update_column_mapping_preset($scope.org_id, preset_id, updated_data).then(function (result) {
            $uibModalInstance.close(result.data.name);
          });
        }
      };

      $scope.remove_preset = function () {
        column_mappings_service.delete_column_mapping_preset($scope.org_id, $scope.data.id).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.new_preset = function () {
        if (!$scope.disabled()) {
          column_mappings_service.new_column_mapping_preset_for_org($scope.org_id, {
            name: $scope.newName,
            mappings: $scope.data.mappings,
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
