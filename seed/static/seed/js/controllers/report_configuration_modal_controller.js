/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.report_configuration_modal', []).controller('report_configuration_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'report_configurations_service',
  'action',
  'data',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, report_configurations_service, action, data) {
    $scope.action = action;
    $scope.data = data;

    $scope.rename_report_configuration = () => {
      if (!$scope.disabled()) {
        const { id } = $scope.data;
        const report_configuration = _.omit($scope.data, 'id');
        report_configuration.name = $scope.newName;
        report_configurations_service
          .update_report_configuration(id, report_configuration)
          .then((result) => {
            $uibModalInstance.close(result.name);
          })
          .catch(() => {
            $uibModalInstance.dismiss();
          });
      }
    };

    $scope.remove_report_configuration = () => {
      report_configurations_service
        .remove_report_configuration($scope.data.id)
        .then(() => {
          $uibModalInstance.close();
        })
        .catch(() => {
          $uibModalInstance.dismiss();
        });
    };

    $scope.new_report_configuration = () => {
      if (!$scope.disabled()) {
        report_configurations_service
          .new_report_configuration({
            name: $scope.newName,
            x_column: $scope.data.x_column,
            y_column: $scope.data.y_column,
            access_level_instance_id: $scope.data.access_level_instance_id,
            access_level_depth: $scope.data.access_level_depth,
            cycles: $scope.data.cycles,
            filter_group_id: $scope.data.filter_group_id
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
