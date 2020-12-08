/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_analyses', [])
  .controller('inventory_detail_analyses_controller', [
    '$state',
    '$scope',
    '$stateParams',
    '$uibModal',
    '$window',
    'inventory_service',
    'inventory_payload',
    // 'analyses_payload',
    'urls',
    'user_service',
    '$log',
    function (
      $state,
      $scope,
      $stateParams,
      $uibModal,
      $window,
      inventory_service,
      inventory_payload,
      // analyses_payload,
      urls,
      user_service,
      $log
    ) {
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = user_service.get_organization();
      // $scope.analyses = analyses_payload.analyses;

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      $scope.open_analysis_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/inventory_detail_analyses_modal.html',
          controller: 'inventory_detail_analyses_modal_controller',
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
