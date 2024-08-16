/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.auth', []).factory('auth_service', [
  '$http',
  'user_service',
  ($http, user_service) => {
    const auth_factory = {};

    /**
     * checks against the auth backend to determine if the requesting user is
     * authorized for a given action. This should happen once per page view.
     *
     * e.g., from the route dispatcher:
     *  auth_service.is_authorized(org_id, ['can_invite_member', 'can_remove_member'])
     *    .then(function(data) {
     *      auth = data.auth; // auth === {'can_invite_member': true, 'can_remove_member': true}
     *  });
     *
     * @param {number} organization_id - id of organization
     * @param {string[]} actions - an array of actions
     * @return {Promise<Object>} A promise that resolves to an object containing:
     *  * - `status`: A string that indicates the success of the operation.
     *  * - `auth`: An object mapping string keys to boolean values representing authorization statuses.
     */
    auth_factory.is_authorized = (organization_id, actions) => user_service.get_user_id().then((user_id) => $http
      .post(
        `/api/v3/users/${user_id}/is_authorized/`,
        {
          actions
        },
        {
          params: {
            organization_id
          }
        }
      )
      .then((response) => response.data));

    return auth_factory;
  }
]);
