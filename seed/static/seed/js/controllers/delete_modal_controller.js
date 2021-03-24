/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_modal', [])
  .controller('delete_modal_controller', [
    '$scope',
    '$q',
    '$uibModalInstance',
    'inventory_service',
    'property_view_ids',
    'taxlot_view_ids',
    function ($scope, $q, $uibModalInstance, inventory_service, property_view_ids, taxlot_view_ids) {
      $scope.property_view_ids = _.uniq(property_view_ids);
      $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);
      $scope.delete_state = 'delete';

      $scope.delete_inventory = function () {
        $scope.delete_state = 'prepare';

        var promises = [];

        if ($scope.property_view_ids.length) promises.push(inventory_service.delete_property_states($scope.property_view_ids));
        if ($scope.taxlot_view_ids.length) promises.push(inventory_service.delete_taxlot_states($scope.taxlot_view_ids));

        return $q.all(promises).then(function (results) {
          $scope.deletedProperties = 0;
          $scope.deletedTaxlots = 0;
          _.forEach(results, function (result, index) {
            if (result.data.status === 'success') {
              if (index === 0 && $scope.property_view_ids.length) $scope.deletedProperties = result.data.properties;
              else $scope.deletedTaxlots = result.data.taxlots;
            }
          });

          if ($scope.property_view_ids.length !== $scope.deletedProperties || $scope.taxlot_view_ids.length !== $scope.deletedTaxlots) {
            $scope.delete_state = 'incomplete';
            return;
          }
          $scope.delete_state = 'success';
        }).catch(function (resp) {
          $scope.delete_state = 'fail';
          if (resp.status === 422) {
            $scope.error = resp.data.message;
          } else {
            $scope.error = resp.data.message;
          }
        });
      };

      /**
       * cancel: dismisses the modal
       */
      $scope.cancel = function () {
        $uibModalInstance.dismiss({
          delete_state: $scope.delete_state,
          property_view_ids: $scope.property_view_ids,
          taxlot_view_ids: $scope.taxlot_view_ids
        });
      };

      /**
       * close: closes the modal
       */
      $scope.close = function () {
        $uibModalInstance.close({
          delete_state: $scope.delete_state,
          property_view_ids: $scope.property_view_ids,
          taxlot_view_ids: $scope.taxlot_view_ids
        });
      };
    }]);
