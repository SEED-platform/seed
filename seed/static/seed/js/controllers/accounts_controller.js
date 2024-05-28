/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
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

    /**
     * Sorts the owners in ascending order by 'last_name', then 'first_name', or otherwise email
     *
     * @param {Array.<{first_name: string, last_name: string, email: string, id: number}>} owners - Array of owner objects to be sorted
     * @returns {Array.<string>}
     */
    $scope.sortOwners = (owners) => owners.sort((a, b) => {
      // Compare by last name
      if (a.last_name && b.last_name) {
        if (a.last_name.toLowerCase() === b.last_name.toLowerCase()) {
          return a.first_name.toLowerCase().localeCompare(b.first_name.toLowerCase());
        }
        return a.last_name.toLowerCase().localeCompare(b.last_name.toLowerCase());
      }
      if (a.last_name) return -1; // a has last_name, b does not
      if (b.last_name) return 1; // b has last_name, a does not

      // If both are missing last names, check first names
      if (a.first_name && b.first_name) {
        return a.first_name.toLowerCase().localeCompare(b.first_name.toLowerCase());
      }
      if (a.first_name) return -1;
      if (b.first_name) return 1;

      // If both are missing first and last names, sort by email
      return a.email.toLowerCase().localeCompare(b.email.toLowerCase());
    }).map((user) => `${user.first_name} ${user.last_name}`.trim() || user.email);

    init();
  }
]);
