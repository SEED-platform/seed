/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.accounts', []).controller('accounts_controller', [
  '$scope',
  '$uibModal',
  'organization_payload',
  'urls',
  'organization_service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModal, organization_payload, urls, organization_service) {
    const init = () => {
      $scope.orgs = organization_payload.organizations;
      $scope.orgs_I_own = organization_payload.organizations.filter((o) => o.user_is_owner);
    };

    $scope.create_sub_organization_modal = (org) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/create_sub_organization_modal.html`,
        controller: 'create_sub_organization_modal_controller',
        resolve: {
          organization: () => org
        }
      });
      modalInstance.result.then(
        () => {
          organization_service.get_organizations().then((data) => {
            organization_payload = data;
            $scope.$emit('organization_list_updated');
            init();
          });
        },
        () => {
          // Do nothing
        }
      );
    };

    init();
  }
]);
