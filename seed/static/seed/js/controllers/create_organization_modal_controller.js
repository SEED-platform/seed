/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.create_organization_modal', [])
  .controller('create_organization_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'user_service',
    'user_id',
    'organization_service',
    function (
      $scope,
      $uibModalInstance,
      user_service,
      user_id,
      organization_service
    ) {

      user_service.get_user_profile().then (function (data) {
        $scope.email = data.email;
      });

      //This in the pattern that the organization service understands
      $scope.org = {
        email: {
          email: $scope.email,
          user_id: user_id
        }
      };

      /**
       * adds a user to the org
       */
      $scope.submit_form = function () {
        const org = _.cloneDeep($scope.org);
        organization_service.add(org).then(function () {
          window.location.href = '/app';
        }).catch(function (error) {
          $scope.error_message = error.data.message;
        });
      };

      $scope.close = function () {
        $uibModalInstance.close();
      };

    }]);
