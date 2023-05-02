/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.profile', [])
  .controller('profile_controller', [
    '$scope',
    'urls',
    'auth_payload',
    'user_profile_payload',
    'user_service',
    function (
      $scope,
      urls,
      auth_payload,
      user_profile_payload,
      user_service
    ) {
      $scope.is_superuser = auth_payload.auth.requires_superuser;
      $scope.user = user_profile_payload;
      $scope.user_updated = false;
      var user_copy = angular.copy($scope.user);
      $scope.username = user_profile_payload.first_name + ' ' + user_profile_payload.last_name;

      /**
       * updates the user's PI
       */
      $scope.submit_form = function () {
        user_service.update_user($scope.user).then(function () {
          $scope.user_updated = true;
          user_copy = angular.copy($scope.user);
          $scope.username = user_profile_payload.first_name + ' ' + user_profile_payload.last_name;
        });
      };

      /**
       * resets the form
       */
      $scope.reset_form = function () {
        $scope.user = angular.copy(user_copy);
      };

    }]);
