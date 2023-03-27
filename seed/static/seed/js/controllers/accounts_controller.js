/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.accounts', [])
  .controller('accounts_controller', [
    '$scope',
    '$uibModal',
    'organization_payload',
    'urls',
    'organization_service',
    function ($scope, $uibModal, organization_payload, urls, organization_service) {

      $scope.create_sub_organization_modal = function (org) {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/create_sub_organization_modal.html',
          controller: 'create_sub_organization_modal_controller',
          resolve: {
            organization: function () {
              return org;
            }
          }
        });
        modalInstance.result.then(function () {
          organization_service.get_organizations().then(function (data) {
            organization_payload = data;
            $scope.$emit('organization_list_updated');
            init();
          });
        }, function () {
          // Do nothing
        });
      };

      var init = function () {
        $scope.orgs = organization_payload.organizations;
        $scope.orgs_I_own = organization_payload.organizations.filter(function (o) {
          return o.user_is_owner;
        });
      };
      init();

    }
  ]);
