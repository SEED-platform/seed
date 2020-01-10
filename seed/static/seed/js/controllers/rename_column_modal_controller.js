/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.rename_column_modal', [])
  .controller('rename_column_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'all_column_names',
    'column_id',
    'column_name',
    'columns_service',
    'spinner_utility',
    function (
      $scope,
      $state,
      $uibModalInstance,
      all_column_names,
      column_id,
      column_name,
      columns_service,
      spinner_utility
    ) {
      $scope.step = {
        number: 1
      };

      $scope.current_column_name = column_name;
      $scope.all_column_names = all_column_names;

      $scope.column = {
        id: column_id,
        name: '',
        exists: false
      };

      $scope.settings = {
        user_acknowledgement: false,
        overwrite_preference: false
      };

      $scope.check_name_exists = function () {
        $scope.column.exists = _.find($scope.all_column_names, function (col_name) {
          return col_name === $scope.column.name;
        });
      };

      $scope.accept_rename = function () {
        spinner_utility.show();
        columns_service.rename_column($scope.column.id, $scope.column.name, $scope.settings.overwrite_preference)
          .then(function (response) {
            $scope.results = {
              success: response.data.success,
              message: response.data.message
            };
            $scope.step.number = 2;
            spinner_utility.hide();
          });
      };

      $scope.dismiss_and_refresh = function () {
        $state.reload();
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.close();
      };

      $scope.valid = function () {
        if (!$scope.column.name || $scope.column.name === $scope.current_column_name) return false;

        if ($scope.column.exists) {
          return $scope.settings.user_acknowledgement && $scope.settings.overwrite_preference;
        } else {
          return $scope.settings.user_acknowledgement;
        }
      };
    }]);
