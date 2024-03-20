/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.export_buildingsync_modal', []).controller('export_buildingsync_modal_controller', [
  '$http',
  '$window',
  '$scope',
  '$uibModalInstance',
  'property_view_id',
  'column_mapping_profiles',
  'user_service',
  // eslint-disable-next-line func-names
  function ($http, $window, $scope, $uibModalInstance, property_view_id, column_mapping_profiles, user_service) {
    $scope.column_mapping_profiles = column_mapping_profiles;
    $scope.current_column_mapping_profile = column_mapping_profiles[0];

    $scope.download_file = () => {
      const the_url = `/api/v3/properties/${property_view_id}/building_sync/`;
      $http
        .get(the_url, {
          params: {
            profile_id: $scope.current_column_mapping_profile.id,
            organization_id: user_service.get_organization().id
          }
        })
        .then(
          (response) => {
            const blob = new Blob([response.data], { type: 'application/xml;charset=utf-8;' });
            const downloadLink = angular.element('<a></a>');
            const filename = `buildingsync_property_${property_view_id}.xml`;
            downloadLink.attr('href', $window.URL.createObjectURL(blob));
            downloadLink.attr('download', filename);
            downloadLink[0].click();
            $uibModalInstance.close();
          },
          (err) => {
            $scope.download_error_message = err.data ? err.data : err.toString();
          }
        );
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
]);
