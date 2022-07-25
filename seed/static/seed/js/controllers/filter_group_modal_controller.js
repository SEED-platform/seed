/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.filter_group_modal', [])
  .controller('filter_group_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'action',
    'filter_groups_service',
    'data',
    'org_id',
    function ($scope, $uibModalInstance, action, filter_groups_service, data, org_id) {
      $scope.action = action;
      $scope.data = data;
      $scope.org_id = org_id;

      $scope.rename_filter_group = function () {
        if (!$scope.disabled()) {
          var filter_group_id = $scope.data.id;
          var updated_data = {name: $scope.newName};
          filter_groups_service.update_filter_group($scope.org_id, filter_group_id, updated_data).then(function (result) {
            $uibModalInstance.close(result.data.name);
          });
        }
      };

      $scope.remove_filter_group = function () {
        filter_groups_service.delete_filter_group($scope.org_id, $scope.data.id).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.new_filter_group = function () {
        if (!$scope.disabled()) {
          filter_groups_service.new_filter_group_for_org($scope.org_id, {
            name: $scope.newName,
            query_dict: $scope.data.query_dict,
            inventory_type: $scope.data.inventory_type
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
