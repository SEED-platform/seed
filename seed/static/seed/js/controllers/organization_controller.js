/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization', []).controller('organization_controller', [
  '$scope',
  '$uibModal',
  'users_payload',
  'organization_payload',
  'auth_payload',
  'organization_service',
  'urls',
  // eslint-disable-next-line func-names
  function ($scope, $uibModal, users_payload, organization_payload, auth_payload, organization_service, urls) {
    $scope.users = users_payload.users;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.new_member_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/new_member_modal.html`,
        controller: 'new_member_modal_controller'
      });
    };

    /**
     * open the create a sub org modal
     */
    $scope.create_sub_organization_modal = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/create_sub_organization_modal.html`,
        controller: 'create_sub_organization_modal_controller',
        resolve: {
          organization: () => $scope.org
        }
      });
      modalInstance.result.then(
        () => {
          organization_service.get_organization($scope.org.id).then((data) => {
            $scope.org = data.organization;
          });
        },
        () => {
          // dismiss
        }
      );
    };
  }
]);
