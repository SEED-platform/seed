/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.create_column_modal', [])
  .controller('create_column_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'uiGridConstants',
    'spinner_utility',
    'Notification',
    'columns_service',
    'org_id',
    'table_name',
    'black_listed_names',
    function (
      $scope,
      $state,
      $uibModalInstance,
      uiGridConstants,
      spinner_utility,
      Notification,
      columns_service,
      org_id,
      table_name,
      black_listed_names,
    ) {
      $scope.column = {
        column_name: "",
        table_name: table_name,
      };

      $scope.create_column = () => {
        if (black_listed_names.includes($scope.column.column_name)){
          Notification.error('This name is being used.');
          return;
        }
        spinner_utility.show()
        columns_service.create_column_for_org(org_id, $scope.column).
        then(() => {
          $uibModalInstance.close();
          $state.reload();
        }).catch((err) => {
          Notification.error('error: ' + err);
        }).finally(() => {
          spinner_utility.hide()
        })
      }
    }]);
