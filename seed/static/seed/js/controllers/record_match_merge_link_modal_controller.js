/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.record_match_merge_link_modal', [])
  .controller('record_match_merge_link_modal_controller', [
    '$scope',
    '$q',
    '$uibModalInstance',
    'headers',
    'inventory_service',
    'inventory_type',
    'organization_id',
    'organization_service',
    function (
      $scope,
      $q,
      $uibModalInstance,
      headers,
      inventory_service,
      inventory_type,
      organization_id,
      organization_service
    ) {
      $scope.headers = headers;

      $scope.inventory_type = inventory_type;
      if (inventory_type === 'properties') {
        $scope.table_name = 'PropertyState';
      } else if (inventory_type === 'taxlots') {
        $scope.table_name = 'TaxLotState';
      }

      $scope.helpBtnText = 'Expand Help';

      $scope.changeHelpBtnText = function (helpBtnText) {
        if (helpBtnText === 'Collapse Help') {
          $scope.helpBtnText = 'Expand Help';
        } else {
          $scope.helpBtnText = 'Collapse Help';
        }
      };

      var promises = [
        organization_service.matching_criteria_columns(organization_id)
      ];

      if (inventory_type === 'properties') {
        promises.unshift(inventory_service.get_property_columns());
      } else if (inventory_type === 'taxlots') {
        promises.unshift(inventory_service.get_taxlot_columns());
      }

      $scope.matching_criteria_columns = ['Loading...'];

      $q.all(promises).then(function (results) {
        var inventory_columns = _.filter(results[0], {table_name: $scope.table_name});
        var raw_column_names = results[1][$scope.table_name];

        // Use display names to identify matching criteria columns.
        $scope.matching_criteria_columns = _.map(raw_column_names, function (col_name) {
          return _.find(inventory_columns, {column_name: col_name}).displayName;
        });
      });

      $scope.close = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
