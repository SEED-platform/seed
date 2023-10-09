/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.filter_group_modal', []).controller('filter_group_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'filter_groups_service',
  'action',
  'data',
  function ($scope, $uibModalInstance, filter_groups_service, action, data) {
    $scope.action = action;
    $scope.data = data;

    $scope.rename_filter_group = function () {
      if (!$scope.disabled()) {
        const { id } = $scope.data;
        const filter_group = _.omit($scope.data, 'id');
        filter_group.name = $scope.newName;
        filter_groups_service
          .update_filter_group(id, filter_group)
          .then((result) => {
            $uibModalInstance.close(result.name);
          })
          .catch(() => {
            $uibModalInstance.dismiss();
          });
      }
    };

    $scope.remove_filter_group = function () {
      filter_groups_service
        .remove_filter_group($scope.data.id)
        .then(() => {
          $uibModalInstance.close();
        })
        .catch(() => {
          $uibModalInstance.dismiss();
        });
    };

    $scope.new_filter_group = function () {
      if (!$scope.disabled()) {
        filter_groups_service
          .new_filter_group({
            name: $scope.newName,
            query_dict: $scope.data.query_dict,
            inventory_type: $scope.data.inventory_type,
            labels: $scope.data.labels,
            label_logic: $scope.data.label_logic
          })
          .then((result) => {
            $uibModalInstance.close(result);
          });
      }
    };

    $scope.disabled = function () {
      if ($scope.action === 'rename') {
        return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
      }
      if ($scope.action === 'new') {
        return _.isEmpty($scope.newName);
      }
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss();
    };
  }
]);
