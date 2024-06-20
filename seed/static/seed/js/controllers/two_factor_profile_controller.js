/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.two_factor_profile', []).controller('two_factor_profile_controller', [
    '$scope',
    "$uibModal",
    'urls',
    'two_factor_service',
    'user_service',
    'auth_payload',
    'organization_payload',
    'user_profile_payload',

    // eslint-disable-next-line func-names
    function (
        $scope,
        $uibModal,
        urls,
        two_factor_service,
        user_service,
        auth_payload,
        organization_payload,
        user_profile_payload,
    ) {
        $scope.is_superuser = auth_payload.auth.requires_superuser;
        $scope.organization = organization_payload.organization;
        $scope.require_2fa = $scope.organization.require_2fa;
        $scope.user = user_profile_payload;
        $scope.temp_user = {...$scope.user};
        const email = $scope.user.email;

        $scope.generate_qr_code = () => {
            two_factor_service.generate_qr_code(email).then((response) => {
                $scope.qr_code_img = 'data:image/png;base64,' + response.data.qr_code;
                open_qr_code_scan_modal()
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
                // refetch user payload
                user_service.get_user_profile().then((user) => {
                    $scope.user = user;
                    if (response.qr_code) {
                        $scope.qr_code_img = 'data:image/png;base64,' + response.qr_code;
                        open_qr_code_scan_modal()
                    }
                })
                console.log(response)
            })
        }

        const open_qr_code_scan_modal = () => {
            const modal_instance = $uibModal.open({
                templateUrl: `${urls.static_url}seed/partials/qr_code_scan_modal.html`,
                controller: 'qr_code_scan_modal_controller',
                backdrop: 'static',
                resolve: {
                    qr_code_img: () => $scope.qr_code_img,
                    require_2fa: () => $scope.require_2fa,
                    user: () => $scope.user,
                }
            })
            modal_instance.result.then((verified) => {
                if (!verified) {
                    methods = {
                        disabled: !$scope.require_2fa,
                        email: $scope.require_2fa,
                        token: false,
                    };
                    two_factor_service.set_method($scope.user.email, methods)
                }
            })
            .finally(() => refresh_user())
            .catch((error) => {
                console.log(error)
            })
        }

        const refresh_user = () => {
            user_service.get_user_profile().then((user) => {
                $scope.user = user
                $scope.temp_user = { ...user }
            })
        }

    }
]);