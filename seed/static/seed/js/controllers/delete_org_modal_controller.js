/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.delete_org_modal', []).controller('delete_org_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'organization_service',
  'uploader_service',
  'org',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, organization_service, uploader_service, org) {
    $scope.org = org;
    $scope.status = {
      in_progress: false,
      progress: 0
    };

    $scope.delete_org = () => {
      $scope.status.in_progress = true;

      organization_service.delete_organization($scope.org.id).then((data) => {
        uploader_service.check_progress_loop(
          data.progress_key,
          0,
          1,
          () => {
            // Reload and go to home page
            window.location.href = '/app';
          },
          () => {
            console.error('Deleting org failed');
            $scope.status.in_progress = false;
          },
          $scope.status
        );
      });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };

    $scope.valid = () => $scope.confirmOrgName && $scope.confirmOrgName.toLowerCase() === org.name.toLowerCase();
  }
]);
