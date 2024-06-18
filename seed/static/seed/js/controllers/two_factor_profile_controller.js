/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.two_factor_profile', []).controller('two_factor_profile_controller', [
    '$scope',
    'two_factor_service',
    'auth_payload',
    'user_profile_payload',

    // eslint-disable-next-line func-names
    function (
        $scope,
        two_factor_service,
        auth_payload,
        user_profile_payload,
    ) {
        $scope.test = "ABC"
        $scope.user = user_profile_payload
        $scope.email_method = $scope.user.two_factor_method == "email"
        $scope.token_method = $scope.user.two_factor_method == "token"


        $scope.save_settings = () => {
            methods = {
                email: $scope.email_method,
                token: $scope.token_method
            }
            two_factor_service.set_method($scope.user.email, methods)

        }

    }
]);