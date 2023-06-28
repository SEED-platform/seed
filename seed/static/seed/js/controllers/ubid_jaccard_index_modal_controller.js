/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_jaccard_index_modal', [])
  .controller('ubid_jaccard_index_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'ubids',
    'ubid_service',
    (
      $scope,
      $uibModalInstance,
      ubids,
      ubid_service
    ) => {
      $scope.ubid1 = ubids[0];
      $scope.ubid2 = ubids[1];

      $scope.valid_ubids = () => {
        return ubid_service.validate_ubid_js($scope.ubid1) && ubid_service.validate_ubid_js($scope.ubid2);
      };

      $scope.edit = () => {
        $scope.editing = true;
        delete $scope.jaccard_index;
      };

      $scope.compare_ubids = () => {
        if (!$scope.valid_ubids()) return;

        ubid_service.compare_ubids($scope.ubid1, $scope.ubid2).then((result) => {
          if (result.status === 'success') {
            $scope.editing = false;
            $scope.jaccard_index = parseFloat(parseFloat(result.data).toFixed(3));
          } else {
            $scope.edit();
          }
        });
      };

      $scope.editing = !$scope.valid_ubids();
      if (!$scope.editing) $scope.compare_ubids();

      $scope.jaccard_quality = (jaccard) => {
        return jaccard <= 0 ? 'No Match' :
          jaccard < 0.5 ? 'Poor' :
            jaccard < 1 ? 'Good' :
              'Perfect';
      };

      $scope.close = () => {
        $uibModalInstance.close();
      };

    }
  ]);
