/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.ubid_decode_modal', []).controller('ubid_decode_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'property_view_ids',
  'taxlot_view_ids',
  'ubid_service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, property_view_ids, taxlot_view_ids, ubid_service) {
    $scope.property_view_ids = _.uniq(property_view_ids);
    $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);

    $scope.total_selected_count = $scope.property_view_ids.length + $scope.taxlot_view_ids.length;

    ubid_service.decode_results($scope.property_view_ids, $scope.taxlot_view_ids).then((result) => {
      $scope.pre_decode_ubid_not_decoded = result.ubid_not_decoded;
      $scope.pre_decode_ubid_successfully_decoded = result.ubid_successfully_decoded;
      $scope.pre_decode_ubid_unpopulated = result.ubid_unpopulated;

      $scope.decode_ubid_state = 'verify';
    });

    $scope.decode_ubids = () => {
      if ($scope.property_view_ids) {
        ubid_service.decode_by_ids($scope.property_view_ids, $scope.taxlot_view_ids).then(() => {
          $scope.decode_ubid_state = 'decoding';

          ubid_service.decode_results($scope.property_view_ids, $scope.taxlot_view_ids).then((result) => {
            $scope.post_decode_ubid_not_decoded = result.ubid_not_decoded;
            $scope.post_decode_ubid_successfully_decoded = result.ubid_successfully_decoded;
            $scope.post_decode_ubid_unpopulated = result.ubid_unpopulated;

            $scope.decode_ubid_state = 'result';
          });
        });
      }
    };

    /**
     * cancel: dismisses the modal
     */
    $scope.cancel = () => {
      $uibModalInstance.dismiss({
        decode_ubid_state: $scope.decode_ubid_state,
        property_view_ids: $scope.property_view_ids,
        taxlot_view_ids: $scope.taxlot_view_ids
      });
    };

    /**
     * close: closes the modal
     */
    $scope.close = () => {
      $uibModalInstance.close({
        decode_ubid_state: $scope.decode_ubid_state,
        property_view_ids: $scope.property_view_ids,
        taxlot_view_ids: $scope.taxlot_view_ids
      });
    };
  }
]);
