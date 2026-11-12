/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// Superusers see every organization, but can only use the ones they are a member of. This offers to add them as an owner.
angular.module('SEED.controller.join_organization_modal', []).controller('join_organization_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'organization_service',
  'user_service',
  'organization',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, organization_service, user_service, organization) {
    $scope.organization = organization;
    $scope.joining = false;
    $scope.error_message = null;

    $scope.join = () => {
      $scope.joining = true;
      $scope.error_message = null;
      return user_service
        .get_user_id()
        .then((user_id) => organization_service.add_user_to_org({ organization: { org_id: organization.id }, user: { user_id } }))
        .then(() => {
          $uibModalInstance.close();
        })
        .catch((err) => {
          $scope.error_message = err.data?.message || err.statusText || 'Failed to add you to the organization';
          $scope.joining = false;
        });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };
  }
]);
