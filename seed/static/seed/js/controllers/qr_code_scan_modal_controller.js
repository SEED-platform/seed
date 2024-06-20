/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.qr_code_scan_modal', []).controller('qr_code_scan_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'Notification',
    'user_service',
    'two_factor_service',
    'qr_code_img',
    'require_2fa',
    'user',
    function ($scope, $uibModalInstance, Notification, user_service, two_factor_service, qr_code_img, require_2fa, user) {
        $scope.qr_code_img = qr_code_img;
        $scope.user = user;
        $scope.code = null;
        let verified = false;


        $scope.generate_qr_code = () => {
            two_factor_service.generate_qr_code(user.email).then((response) => {
                $scope.qr_code_img = 'data:image/png;base64,' + response.data.qr_code;
            })
        }

        $scope.verify_token = (code) => {
            console.log(code)
            two_factor_service.verify_code(code, $scope.user.email).then((response) => {

                console.log(response)
                if (response.data.success) {
                    Notification.success("Authenticator App Verified!")
                    verified = true
                    $scope.close(verified)
                } else if (response.data.error) {
                    Notification.error("Unable to verify code. Please try again.")
                }
            })
        }

        // if a user is unable to use a qr code, set method to disabled and close
        $scope.other_method = () => {
            methods = {
                disabled: !require_2fa,
                email: require_2fa,
                token: false,
            };
            two_factor_service.set_method($scope.user.email, methods).then(() => {
                user_service.get_user_profile().then(() => {
                    $uibModalInstance.close(verified)
                })
            })
        }

        $scope.close = () => {
            $uibModalInstance.close(verified);
        };
    }
]);
