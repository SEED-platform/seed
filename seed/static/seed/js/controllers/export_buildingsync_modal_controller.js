/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.export_buildingsync_modal', [])
  .controller('export_buildingsync_modal_controller', [
    '$http',
    '$window',
    '$scope',
    '$uibModalInstance',
    'property_view_id',
    'column_mapping_presets',
    function (
      $http,
      $window,
      $scope,
      $uibModalInstance,
      property_view_id,
      column_mapping_presets
    ) {
      $scope.column_mapping_presets = column_mapping_presets;
      $scope.current_column_mapping_preset = column_mapping_presets[0];

      $scope.download_file = function () {
        var the_url = '/api/v2_1/properties/' + property_view_id + '/building_sync/';
        $http.get(
          the_url,
          { params: { preset_id: $scope.current_column_mapping_preset.id } }
        ).then(function (response) {
          var blob = new Blob([response.data], {type: 'application/xml;charset=utf-8;'});
          var downloadLink = angular.element('<a></a>');
          var filename = 'buildingsync_property_' + property_view_id + '.xml';
          downloadLink.attr('href', $window.URL.createObjectURL(blob));
          downloadLink.attr('download', filename);
          downloadLink[0].click();
          $uibModalInstance.close();
        }, function (err) {
          $scope.download_error_message = err.data ? err.data : err.toString();
        });
      };

      $scope.close = function () {
        $uibModalInstance.close();
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };
    }]);
