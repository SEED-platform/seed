/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_modal', [])
  .controller('delete_modal_controller', [
    '$scope',
    '$q',
    '$uibModalInstance',
    'inventory_service',
    'analyses_service',
    'property_view_ids',
    'taxlot_view_ids',
    function ($scope, $q, $uibModalInstance, inventory_service, analyses_service, property_view_ids, taxlot_view_ids) {
      $scope.property_view_ids = _.uniq(property_view_ids);
      $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);
      $scope.delete_state = 'delete';
      $scope.delete_analyses = true;
      $scope.delete_batch_analyses = false;


      let analysis_ids = [];
      let batch_analysis_ids = [];
      for (i in $scope.property_view_ids) {
        inventory_service.get_property($scope.property_view_ids[i]).then(function (results) {
          analyses_service.get_analyses_for_canonical_property(results.property.id).then(function (results) {
            for (i in results.analyses) {
              if (results.analyses[i].number_of_analysis_property_views > 1) {
                batch_analysis_ids.push(results.analyses[i].id);
              } else {
                analysis_ids.push(results.analyses[i].id);
              }
            }
            $scope.analysis_ids = _.uniq(analysis_ids);
            $scope.batch_analysis_ids = _.uniq(batch_analysis_ids);
          });
        });
      }

      $scope.delete_inventory = function () {
        $scope.delete_state = 'prepare';

        var promises = [];

        if ($scope.property_view_ids.length) promises.push(inventory_service.delete_property_states($scope.property_view_ids));
        if ($scope.taxlot_view_ids.length) promises.push(inventory_service.delete_taxlot_states($scope.taxlot_view_ids));
        if ($scope.delete_analyses) for (i in $scope.analysis_ids) promises.push(analyses_service.delete_analysis($scope.analysis_ids[i]));
        if ($scope.delete_batch_analyses) for (i in $scope.batch_analysis_ids) promises.push(analyses_service.delete_analysis($scope.batch_analysis_ids[i]));

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
