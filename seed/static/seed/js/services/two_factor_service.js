/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.two_factor', []).factory('two_factor_service', [
    '$http',
    'user_service',
    ($http, user_service) => {
        const two_factor_factory = {};

        two_factor_factory.set_method = (user_email, methods) => {
            $http.post(
                '/api/v3/two_factor/set_method/',
                {
                    user_email: user_email,
                    methods: methods,
                },
                {
                    params: {
                        organization_id: user_service.get_organization().id
                    }
                }
            )
            .then((response) => {
                console.log(response)
                return response
            })
        }

        return two_factor_factory

    }
])
