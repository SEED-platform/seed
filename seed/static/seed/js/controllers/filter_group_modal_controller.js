/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.filter_group_modal', []).controller('filter_group_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'filter_groups_service',
  'action',
  'data',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, filter_groups_service, action, data) {
    $scope.action = action;
    $scope.data = data;

    $scope.rename_filter_group = () => {
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

    $scope.remove_filter_group = () => {
      filter_groups_service
        .remove_filter_group($scope.data.id)
        .then(() => {
          $uibModalInstance.close();
        })
        .catch(() => {
          $uibModalInstance.dismiss();
        });
    };

    $scope.new_filter_group = () => {
      if (!$scope.disabled()) {
        filter_groups_service
          .new_filter_group({
            name: $scope.newName,
            query_dict: $scope.data.query_dict,
            inventory_type: $scope.data.inventory_type,
            and_labels: $scope.data.and_labels,
            or_labels: $scope.data.or_labels,
            exclude_labels: $scope.data.exclude_labels,
          })
          .then((result) => {
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
