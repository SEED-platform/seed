/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.export_inventory_modal', []).controller('export_inventory_modal_controller', [
  '$http',
  '$scope',
  '$uibModalInstance',
  'user_service',
  'uploader_service',
  'ids',
  'columns',
  'inventory_type',
  'profile_id',
  'spinner_utility',
  'filter_header_string',
  function (
    $http,
    $scope,
    $uibModalInstance,
    user_service,
    uploader_service,
    ids,
    columns,
    inventory_type,
    profile_id,
    spinner_utility,
    filter_header_string
  ) {
    $scope.export_name = '';
    $scope.include_notes = true;
    $scope.include_label_header = false;
    $scope.include_meter_readings = false;
    $scope.inventory_type = inventory_type;
    $scope.exporting = false;
    $scope.exporter_progress = {
      progress: 0,
      status_message: ''
    };

    $scope.export_selected = function (export_type) {
      var filename = $scope.export_name;
      var ext = '.' + export_type;
      if (!_.endsWith(filename, ext)) filename += ext;
      $scope.exporting = true;
      $http.get('/api/v3/tax_lot_properties/start_export/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(data => {
        uploader_service.check_progress_loop(data.data.progress_key, 0, 1,
          function () { },
          function () { },
          $scope.exporter_progress);
        return $http.post('/api/v3/tax_lot_properties/export/', {
          ids: ids,
          filename: filename,
          profile_id: profile_id,
          export_type: export_type,
          include_notes: $scope.include_notes,
          include_meter_readings: $scope.include_meter_readings,
          progress_key: data.data.progress_key
        }, {
          params: {
            organization_id: user_service.get_organization().id,
            inventory_type: inventory_type
          },
          responseType: export_type === 'xlsx' ? 'arraybuffer' : undefined
        });
      }).then(function (response) {
        var blob_type = response.headers()['content-type'];
        var data;
        if (export_type === 'xlsx') {
          data = response.data;
        } else if (blob_type === 'application/json') {
          data = JSON.stringify(response.data, null, '    ');
        } else if (blob_type === 'text/csv') {
          if ($scope.include_label_header) {
            data = [filter_header_string, response.data].join('\r\n');
          } else {
            data = response.data;
          }
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
