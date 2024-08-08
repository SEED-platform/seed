/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.two_factor', []).factory('two_factor_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const two_factor_factory = {};

    two_factor_factory.set_method = (user_email, methods) => $http.post(
      '/api/v3/two_factor/set_method/',
      {
        user_email,
        methods
      },
      {
        params: {
          organization_id: user_service.get_organization().id
        }
      }
    )
      .then((response) => response.data)
      .catch((response) => response);

    two_factor_factory.resend_token_email = (user_email) => $http.post(
      '/api/v3/two_factor/resend_token_email/',
      {
        user_email
      },
      {
        params: {
          organization_id: user_service.get_organization().id
        }
      }
    )
      .then((response) => response)
      .catch((response) => response);

    two_factor_factory.generate_qr_code = (user_email) => $http.post(
      '/api/v3/two_factor/generate_qr_code/',
      {
        user_email
      },
      {
        params: {
          organization_id: user_service.get_organization().id
        }
      }
    )
      .then((response) => response)
      .catch((response) => response);

    two_factor_factory.verify_code = (code, user_email) => $http.post(
      '/api/v3/two_factor/verify_code/',
      {
        code,
        user_email
      },
      {
        params: {
          organization_id: user_service.get_organization().id
        }
      }
    )
      .then((response) => response)
      .catch((response) => response);

    return two_factor_factory;
  }
]);
