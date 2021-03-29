/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.sample_data_modal', [])
  .controller('sample_data_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'organization_service',
    'organization',
    'cycle',
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      organization_service,
      organization,
      cycle
    ) {
      $scope.inProgress = false;
      $scope.hasData = cycle.num_properties > 0 || cycle.num_taxlots > 0;

      $scope.continue = function () {
        $scope.inProgress = true;
        organization_service.insert_sample_data(organization.org_id).then(() => {
          $uibModalInstance.close();
          $state.go('inventory_list', {inventory_type: 'properties'});
        }).catch(response => {
          Notification.error('Error: Failed to insert sample data');
          console.error(response.data);
        }).finally(() => {
          $scope.inProgress = false;
        });
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
