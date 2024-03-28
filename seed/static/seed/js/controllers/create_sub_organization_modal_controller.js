/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.create_sub_organization_modal', []).controller('create_sub_organization_modal_controller', [
  '$scope',
  '$rootScope',
  '$uibModalInstance',
  'organization_service',
  'organization',
  // eslint-disable-next-line func-names
  function ($scope, $rootScope, $uibModalInstance, organization_service, organization) {
    $scope.sub_org = {};
    $scope.error_message = '';

    $scope.org_id = organization.id;
    /**
     * creates a sub organization with an owner
     */
    $scope.submit_form = () => {
      organization_service.create_sub_org(organization, $scope.sub_org).then(
        () => {
          $rootScope.$broadcast('organization_list_updated');
          $uibModalInstance.close();
        },
        (data) => {
          // error data are in the data object
          $scope.error_message = data.data.message;
        }
      );
    };

    $scope.close = () => {
      $uibModalInstance.close();
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    /**
     * set the focus on the first input box
     */
    _.delay(() => {
      angular.element('#createOrganizationName').focus();
    }, 50);

    /**
     * clear the error message when the user starts typing
     */
    $scope.$watch('sub_org.email', () => {
      $scope.error_message = '';
    });
  }
]);
