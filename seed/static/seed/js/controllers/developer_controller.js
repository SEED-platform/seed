/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.developer', []).controller('developer_controller', [
  '$scope',
  '$location',
  'urls',
  'auth_payload',
  'user_profile_payload',
  'user_service',
  // eslint-disable-next-line func-names
  function ($scope, $location, urls, auth_payload, user_profile_payload, user_service) {
    $scope.is_superuser = auth_payload.auth.requires_superuser;
    $scope.user = user_profile_payload;
    $scope.new_key_generated = false;
    $scope.username = `${user_profile_payload.first_name} ${user_profile_payload.last_name}`;

    /**
     * generates a new API key for the user
     */
    $scope.generate_api_key = () => {
      user_service.generate_api_key().then((data) => {
        $scope.user.api_key = data.api_key;
        $scope.new_key_generated = true;
      });
    };

    const protocol = $location.protocol();
    const host = $location.host();
    const port = $location.port();
    let showPort = false;
    if ((protocol === 'http' && port !== 80) || (protocol === 'https' && port !== 443)) showPort = true;

    $scope.getHost = () => `${protocol}://${host}${showPort ? `:${port}` : ''}`;
  }
]);
