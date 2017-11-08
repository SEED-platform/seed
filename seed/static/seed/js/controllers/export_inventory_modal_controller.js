/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.export_inventory_modal', []).controller('export_inventory_modal_controller', [
  '$http',
  '$scope',
  '$uibModalInstance',
  'user_service',
  'cycle_id',
  'ids',
  'columns', function ($http, $scope, $uibModalInstance, user_service, cycle_id, ids, columns) {
    $scope.export_name = '';
    $scope.export_type = 'csv';


    $scope.export_selected = function () {
      var filename = $scope.export_name,
        ext = '.' + $scope.export_type;
      if (!_.endsWith(filename, ext)) filename += ext;

      return $http.post('/api/v2/properties/csv/', {
        columns: columns,
        ids: ids,
        filename: filename
      }, {
        params: {
          organization_id: user_service.get_organization().id,
          cycle_id: cycle_id
        }
      }).then(function (response) {
        var blob = new Blob([response.data], {type: 'text/csv'});
        saveAs(blob, filename);

        $scope.close();
        return response.data;
      });
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = function () {
      $uibModalInstance.close();
    };
  }]);
