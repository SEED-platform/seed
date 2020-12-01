/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_analysis', [])
  .controller('inventory_detail_analysis_controller', [
    '$state',
    '$scope',
    '$stateParams',
    '$uibModal',
    '$window',
    'meter_service',
    'cycles',
    'dataset_service',
    'inventory_service',
    'inventory_payload',
    'meters',
    'property_meter_usage',
    'spinner_utility',
    'urls',
    'user_service',
    '$log',
    function (
      $state,
      $scope,
      $stateParams,
      $uibModal,
      $window,
      meter_service,
      cycles,
      dataset_service,
      inventory_service,
      inventory_payload,
      meters,
      property_meter_usage,
      spinner_utility,
      urls,
      user_service,
      $log
    ) {
      spinner_utility.show();
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = user_service.get_organization();

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      $scope.open_analysis_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/inventory_detail_analysis_modal.html',
          controller: 'inventory_detail_analysis_modal_controller',
          resolve: {
            inventory_ids: function () {
              return [$scope.inventory.view_id];
            },
            inventory_type: function () {
              return $scope.inventory_type;
            }
          }
        });
      };
    }]);
