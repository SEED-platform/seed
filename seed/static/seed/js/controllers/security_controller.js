/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.security', []).controller('security_controller', [
  '$scope',
  'urls',
  'auth_payload',
  'user_service',
  'user_profile_payload',
  // eslint-disable-next-line func-names
  function ($scope, urls, auth_payload, user_service, user_profile_payload) {
    $scope.is_superuser = auth_payload.auth.requires_superuser;
    $scope.username = `${user_profile_payload.first_name} ${user_profile_payload.last_name}`;

    /**
     * sets the user's password
     */
    $scope.change_password = () => {
      user_service.set_password($scope.current_password, $scope.password_1, $scope.password_2).then(
        () => {
          $scope.password_updated = true;
          $scope.error_message = '';
        },
        (response) => {
          $scope.password_updated = false;
          $scope.error_message = response.data.message;
        }
      );
    };
  }
]);
