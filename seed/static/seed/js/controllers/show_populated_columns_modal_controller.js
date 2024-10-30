/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.show_populated_columns_modal', []).controller('show_populated_columns_modal_controller', [
  '$scope',
  '$window',
  '$uibModalInstance',
  'Notification',
  'inventory_service',
  'modified_service',
  'spinner_utility',
  'columns',
  'currentProfile',
  'cycle',
  'provided_inventory',
  'inventory_type',
  // eslint-disable-next-line func-names
  function ($scope, $window, $uibModalInstance, Notification, inventory_service, modified_service, spinner_utility, columns, currentProfile, cycle, provided_inventory, inventory_type) {
    $scope.start = () => {
      $scope.state = 'running';
      $scope.status = 'Processing...';
      $scope.inventory_type = inventory_type === 'properties' ? 'Property' : 'Tax lot';

      inventory_service.update_column_list_profile_to_show_populated(currentProfile.id, cycle.id, $scope.inventory_type).then((/* updatedProfile */) => {
        modified_service.resetModified();
        $scope.progress = 100;
        $scope.state = 'done';
        $scope.refresh();
      });
    };

    $scope.refresh = () => {
      spinner_utility.show();
      $uibModalInstance.close();
      $window.location.reload();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
