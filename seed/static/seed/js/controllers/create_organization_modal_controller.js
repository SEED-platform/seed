/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.create_organization_modal', []).controller('create_organization_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'user_service',
  'user_id',
  'organization_service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, user_service, user_id, organization_service) {
    user_service.get_user_profile().then((data) => {
      $scope.email = data.email;
    });

    // This in the pattern that the organization service understands
    $scope.org = {
      email: {
        email: $scope.email,
        user_id
      }
    };

    /**
     * adds a user to the org
     */
    $scope.submit_form = () => {
      const org = _.cloneDeep($scope.org);
      organization_service
        .add(org)
        .then(() => {
          window.location.href = '/app';
        })
        .catch((error) => {
          $scope.error_message = error.data.message;
        });
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };
  }
]);
