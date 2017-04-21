/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.developer', [])
.controller('developer_controller', [
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
    $scope.user = user_profile_payload;
    $scope.new_key_generated = false;
    $scope.username = user_profile_payload.first_name + ' ' + user_profile_payload.last_name;

    /**
     * generates a new API key for the user
     */
    $scope.generate_api_key = function() {
        user_service.generate_api_key().then(function (data) {
            $scope.user.api_key = data.api_key;
            $scope.new_key_generated = true;
        });
    };

}]);
