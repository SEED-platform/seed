/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.qr_code_scan_modal', []).controller('qr_code_scan_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'user_service',
    'two_factor_service',
    'qr_code_img',
    'user',
    function ($scope, $uibModalInstance, user_service, two_factor_service, qr_code_img, user) {
        $scope.qr_code_img = qr_code_img;
        $scope.user = user;


        $scope.generate_qe_code = () => {
            two_factor_service.generate_qr_code(user.email).then((response) => {
                $scope.qr_code_img = 'data:image/png;base64,' + response.data.qr_code;
            })
        }

        // if a user is unable to use a qr code, set method to disabled and close
        $scope.other_method = () => {
            methods = {
                disabled: true,
                email: false,
                token: false,
            };
            two_factor_service.set_method($scope.user.email, methods).then(() => {
                user_service.get_user_profile().then((user) => {
                    $uibModalInstance.close()
                })
            })
        }

        $scope.close = () => {
            $uibModalInstance.dismiss();
        };
    }
]);
