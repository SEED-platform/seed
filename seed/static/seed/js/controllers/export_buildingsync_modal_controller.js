/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.export_buildingsync_modal', [])
  .controller('export_buildingsync_modal_controller', [
    '$http',
    '$window',
    '$scope',
    '$uibModalInstance',
    'property_view_id',
    'column_mapping_profiles',
    'user_service',
    function (
      $http,
      $window,
      $scope,
      $uibModalInstance,
      property_view_id,
      column_mapping_profiles,
      user_service
    ) {
      $scope.column_mapping_profiles = column_mapping_profiles;
      $scope.current_column_mapping_profile = column_mapping_profiles[0];

      $scope.download_file = function () {
        var the_url = '/api/v3/properties/' + property_view_id + '/building_sync/';
        $http.get(
          the_url,
          {
            params: {
              profile_id: $scope.current_column_mapping_profile.id,
              organization_id: user_service.get_organization().id
            }
          }
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
