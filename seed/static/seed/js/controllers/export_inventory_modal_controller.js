/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.export_inventory_modal', []).controller('export_inventory_modal_controller', [
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
  // eslint-disable-next-line func-names
  function ($http, $scope, $uibModalInstance, user_service, uploader_service, ids, columns, inventory_type, profile_id, spinner_utility, filter_header_string) {
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

    $scope.export_selected = (export_type) => {
      let filename = $scope.export_name;
      const ext = `.${export_type}`;
      if (!filename.endsWith(ext)) filename += ext;
      $scope.exporting = true;

      const successFn = (response) => {
        data = response.message;

        const blob_map = {
          csv: csv_to_blob,
          xlsx: base64_to_blob,
          geojson: geojson_to_blob,
        };

        const blob = blob_map[export_type](data);
        saveAs(blob, filename);
        $scope.close();
      }

      $http.post(
        '/api/v3/tax_lot_properties/export/',
        {
          ids,
          filename,
          profile_id,
          export_type,
          include_notes: $scope.include_notes,
          include_meter_readings: $scope.include_meter_readings,
        },
        {
          params: {
            organization_id: user_service.get_organization().id,
            inventory_type
          },
        }
      ).then((data) => {
        uploader_service.check_progress_loop(
          data.data.progress_key,
          0,
          1,
          successFn,
          () => {},
          $scope.exporter_progress
        )
      })
    }

    const csv_to_blob = (data) => {
      if ($scope.include_label_header) {
        data = [filter_header_string, data].join('\r\n');
      }
      return new Blob([data], { type: 'text/csv'});
    }

    const base64_to_blob = (base64) => {
      const byteCharacters = atob(base64);
      const byteArrays = [];

      for (let i = 0; i < byteCharacters.length; i += 512) {
        const slice = byteCharacters.slice(i, i + 512);
        const byteNumbers = Array.from(slice).map(c => c.charCodeAt(0));
        byteArrays.push(new Uint8Array(byteNumbers));
      }

      return new Blob(byteArrays, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    }

    geojson_to_blob = (data) => {
      data = JSON.stringify(data, null, '    ');
      return new Blob([data], { type: 'application/geo+json' });
    }

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };
  }
]);
