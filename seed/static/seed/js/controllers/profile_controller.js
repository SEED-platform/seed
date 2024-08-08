/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.profile', []).controller('profile_controller', [
  '$scope',
  'urls',
  'auth_payload',
  'user_profile_payload',
  'user_service',
  // eslint-disable-next-line func-names
  function ($scope, urls, auth_payload, user_profile_payload, user_service) {
    $scope.is_superuser = auth_payload.auth.requires_superuser;
    $scope.user = user_profile_payload;
    $scope.user_updated = false;
    let user_copy = angular.copy($scope.user);
    $scope.username = `${user_profile_payload.first_name} ${user_profile_payload.last_name}`;

    /**
     * updates the user's PI
     */
    $scope.submit_form = () => {
      user_service.update_user($scope.user).then(() => {
        $scope.user_updated = true;
        user_copy = angular.copy($scope.user);
        $scope.username = `${user_profile_payload.first_name} ${user_profile_payload.last_name}`;
      });
    };

    /**
     * resets the form
     */
    $scope.reset_form = () => {
      $scope.user = angular.copy(user_copy);
    };
  }
]);
