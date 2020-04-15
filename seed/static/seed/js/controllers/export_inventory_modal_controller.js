/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.export_inventory_modal', []).controller('export_inventory_modal_controller', [
  '$http',
  '$scope',
  '$uibModalInstance',
  'user_service',
  'cycle_id',
  'ids',
  'columns',
  'inventory_type',
  'profile_id',
  function ($http, $scope, $uibModalInstance, user_service, cycle_id, ids, columns, inventory_type, profile_id) {
    $scope.export_name = '';
    $scope.inventory_type = inventory_type;

    $scope.export_selected = function (export_type) {
      var filename = $scope.export_name;

      var ext = '.' + export_type;
      if (!_.endsWith(filename, ext)) filename += ext;

      return $http.post('/api/v2.1/tax_lot_properties/export/', {
        ids: ids,
        filename: filename,
        profile_id: profile_id,
        export_type: export_type
      }, {
        params: {
          organization_id: user_service.get_organization().id,
          cycle_id: cycle_id,
          inventory_type: inventory_type
        },
        responseType: export_type === 'xlsx' ? 'arraybuffer' : undefined
      }).then(function (response) {
        var blob_type = response.headers()['content-type'];
        var data;
        if (export_type === 'xlsx') {
          data = response.data;
        } else if (blob_type === 'application/json') {
          data = JSON.stringify(response.data, null, '    ');
        } else if (blob_type === 'text/csv') {
          data = response.data;
        }

        var blob = new Blob([data], {type: blob_type});
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
