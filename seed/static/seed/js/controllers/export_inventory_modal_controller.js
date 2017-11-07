/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.export_inventory_modal', []).controller('export_inventory_modal_controller', [
  '$http',
  '$scope',
  '$uibModalInstance',
  'user_service',
  'gridApi',
  'uiGridExporterConstants', function ($http, $scope, $uibModalInstance, user_service, gridApi, uiGridExporterConstants) {
    $scope.gridApi = gridApi;
    $scope.export_name = '';
    $scope.export_type = 'csv';


    $scope.export_selected = function () {
      var filename = $scope.export_name,
        ext = '.' + $scope.export_type;
      if (!_.endsWith(filename, ext)) filename += ext;

      return $http.post('/api/v2/properties/csv/', {
        // columns: _.uniq(columns.concat(['property_state_id', 'taxlot_state_id', 'property_view_id', 'taxlot_view_id']))
        filename: filename
      }, {
        params: {
          organization_id: user_service.get_organization().id,
          cycle_id: 2
        }
      }).then(function (response) {
        console.log(response.data);
        return response.data;
      });

      // $scope.gridApi.grid.options.exporterCsvFilename = filename;
      // $scope.gridApi.exporter.csvExport(uiGridExporterConstants.SELECTED, uiGridExporterConstants.VISIBLE);
      $uibModalInstance.close();
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = function () {
      $uibModalInstance.close();
    };
  }]);
