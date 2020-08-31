angular.module('BE.seed.controller.ubid_modal', [])
  .controller('ubid_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'property_view_ids',
    'taxlot_view_ids',
    'ubid_service',
    function ($scope, $uibModalInstance, property_view_ids, taxlot_view_ids, ubid_service) {
      $scope.property_view_ids = _.uniq(property_view_ids);
      $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);

      $scope.total_selected_count = $scope.property_view_ids.length + $scope.taxlot_view_ids.length;

      ubid_service.decode_results($scope.property_view_ids, $scope.taxlot_view_ids).then(function (result) {
        $scope.pre_decode_ubid_not_decoded = result.ubid_not_decoded;
        $scope.pre_decode_ubid_successfully_decoded = result.ubid_successfully_decoded;
        $scope.pre_decode_ubid_unpopulated = result.ubid_unpopulated;

        $scope.pre_decode_ulid_not_decoded = result.ulid_not_decoded;
        $scope.pre_decode_ulid_successfully_decoded = result.ulid_successfully_decoded;
        $scope.pre_decode_ulid_unpopulated = result.ulid_unpopulated;

        $scope.decode_ubid_state = 'verify';
      });

      $scope.decode_ubids = function () {
        if ($scope.property_view_ids) {
          ubid_service.decode_by_ids($scope.property_view_ids, $scope.taxlot_view_ids).then(function () {
            $scope.decode_ubid_state = 'decoding';

            ubid_service.decode_results($scope.property_view_ids, $scope.taxlot_view_ids).then(function (result) {
              $scope.post_decode_ubid_not_decoded = result.ubid_not_decoded;
              $scope.post_decode_ubid_successfully_decoded = result.ubid_successfully_decoded;
              $scope.post_decode_ubid_unpopulated = result.ubid_unpopulated;

              $scope.post_decode_ulid_not_decoded = result.ulid_not_decoded;
              $scope.post_decode_ulid_successfully_decoded = result.ulid_successfully_decoded;
              $scope.post_decode_ulid_unpopulated = result.ulid_unpopulated;

              $scope.decode_ubid_state = 'result';
            });
          });
        }
      };

      /**
       * cancel: dismisses the modal
       */
      $scope.cancel = function () {
        $uibModalInstance.dismiss({
          decode_ubid_state: $scope.decode_ubid_state,
          property_view_ids: $scope.property_view_ids,
          taxlot_view_ids: $scope.taxlot_view_ids
        });
      };

      /**
       * close: closes the modal
       */
      $scope.close = function () {
        $uibModalInstance.close({
          decode_ubid_state: $scope.decode_ubid_state,
          property_view_ids: $scope.property_view_ids,
          taxlot_view_ids: $scope.taxlot_view_ids
        });
      };
    }
  ]);
