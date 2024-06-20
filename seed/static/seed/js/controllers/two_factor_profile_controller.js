/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.two_factor_profile', []).controller('two_factor_profile_controller', [
    '$scope',
    'two_factor_service',
    'user_service',
    'auth_payload',
    'user_profile_payload',

    // eslint-disable-next-line func-names
    function (
        $scope,
        two_factor_service,
        user_service,
        auth_payload,
        user_profile_payload,
    ) {
        $scope.is_superuser = auth_payload.auth.requires_superuser;
        $scope.user = user_profile_payload;
        $scope.temp_user = {...$scope.user};
        const email = $scope.user.email;

        $scope.generate_qe_code = () => {
            console.log('go')
            two_factor_service.generate_qr_code(email).then((response) => {
                $scope.qr_code_image = 'data:image/png;base64,' + response.data.qr_code;
                $scope.new_qr_code = true;
            })
        }

        $scope.resend_token_email = () => {
            two_factor_service.resend_token_email(email).then(() => {
                $scope.email_sent = true;
            })
        }

        $scope.save_settings = () => {
            methods = {
                disabled: $scope.temp_user.two_factor_method == 'disabled',
                email: $scope.temp_user.two_factor_method == 'email',
                token: $scope.temp_user.two_factor_method == 'token',
            };
            two_factor_service.set_method($scope.user.email, methods).then((response) => {
                if (response.qr_code) {
                    $scope.new_qr_code = true;
                    $scope.qr_code_image = 'data:image/png;base64,' + response.qr_code;
                }
                console.log(response)
                
                // refetch user payload
                user_service.get_user_profile().then((response) => {
                    $scope.user = response;
                })
            })
        }

    }
]);