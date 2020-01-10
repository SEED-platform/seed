/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_modal', [])
  .controller('delete_modal_controller', [
    '$scope',
    '$q',
    '$uibModalInstance',
    'inventory_service',
    'property_states',
    'taxlot_states',
    function ($scope, $q, $uibModalInstance, inventory_service, property_states, taxlot_states) {
      $scope.property_states = _.uniq(property_states);
      $scope.taxlot_states = _.uniq(taxlot_states);
      $scope.delete_state = 'delete';

      $scope.delete_inventory = function () {
        $scope.delete_state = 'prepare';

        var promises = [];
        if ($scope.property_states.length) promises.push(inventory_service.delete_property_states($scope.property_states));
        if ($scope.taxlot_states.length) promises.push(inventory_service.delete_taxlot_states($scope.taxlot_states));

        return $q.all(promises).then(function (results) {
          $scope.deletedProperties = 0;
          $scope.deletedTaxlots = 0;
          _.forEach(results, function (result, index) {
            if (result.data.status === 'success') {
              if (index === 0 && $scope.property_states.length) $scope.deletedProperties = result.data.properties;
              else $scope.deletedTaxlots = result.data.taxlots;
            }
          });
          if ($scope.property_states.length !== $scope.deletedProperties || $scope.taxlot_states.length !== $scope.deletedTaxlots) {
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
          property_states: $scope.property_states,
          taxlot_states: $scope.taxlot_states
        });
      };

      /**
       * close: closes the modal
       */
      $scope.close = function () {
        $uibModalInstance.close({
          delete_state: $scope.delete_state,
          property_states: $scope.property_states,
          taxlot_states: $scope.taxlot_states
        });
      };
    }]);
