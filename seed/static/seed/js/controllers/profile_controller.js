/*
 * :copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
    $scope.auth = auth_payload.auth;
    $scope.user = user_profile_payload.user;
    $scope.user_updated = false;
    var user_copy = angular.copy($scope.user);
    $scope.username = user_profile_payload.user.first_name + " " + 
        user_profile_payload.user.last_name;

    /**
     * updates the user's PI
     */
    $scope.submit_form = function () {
        user_service.update_user($scope.user).then(function (data) {
            $scope.user_updated = true;
            user_copy = angular.copy($scope.user);
            $scope.username = user_profile_payload.user.first_name + " " + 
              user_profile_payload.user.last_name;
        });
    };

    /**
     * resets the form
     */
    $scope.reset_form = function () {
        $scope.user = angular.copy(user_copy);
    };

}]);
