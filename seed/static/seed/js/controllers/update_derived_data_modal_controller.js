/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.update_derived_data_modal', []).controller('update_derived_data_modal_controller', [
  '$scope',
  '$q',
  '$uibModalInstance',
  'inventory_service',
  'property_view_ids',
  'taxlot_view_ids',
  // eslint-disable-next-line func-names
  function ($scope, $q, $uibModalInstance, inventory_service, property_view_ids, taxlot_view_ids) {
    $scope.property_view_ids = _.uniq(property_view_ids);
    $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);

    $scope.begin_update = () => {
      inventory_service.update_derived_data($scope.property_view_ids, $scope.taxlot_view_ids).then($uibModalInstance.close);
    };

    /**
     * cancel: dismisses the modal
     */
    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
