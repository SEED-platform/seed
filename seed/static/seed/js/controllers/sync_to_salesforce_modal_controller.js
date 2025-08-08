/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.sync_to_salesforce_modal', []).controller('sync_to_salesforce_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'urls',
  'goal',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, urls, goal) {
    $scope.goal = goal;
    $scope.goal_details = {
        'Partner': $scope.goal.salesforce_partner_id,
        'Partner ID': $scope.goal.salesforce_partner_name,
    };

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };
  }
]);
