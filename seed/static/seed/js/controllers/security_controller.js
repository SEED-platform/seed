/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.security', [])
  .controller('security_controller', [
    '$scope',
    'urls',
    'auth_payload',
    'user_service',
    'user_profile_payload',
    function (
      $scope,
      urls,
      auth_payload,
      user_service,
      user_profile_payload
    ) {
      $scope.is_superuser = auth_payload.auth.requires_superuser;
      $scope.username = user_profile_payload.first_name + ' ' + user_profile_payload.last_name;

      /**
       * sets the user's password
       */
      $scope.change_password = function () {
        user_service.set_password($scope.current_password, $scope.password_1, $scope.password_2).then(function () {
          $scope.password_updated = true;
          $scope.error_message = '';
        }, function (response) {
          $scope.password_updated = false;
          $scope.error_message = response.data.message;
        });
      };

    }]);
