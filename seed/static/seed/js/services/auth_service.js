/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.auth', []).factory('auth_service', [
  '$http',
  'user_service',
  'generated_urls',
  ($http, user_service, generated_urls) => {
    const auth_factory = {};
    const urls = generated_urls;

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
     * @param  {integer}  organization_id is the id of organization
     * @param  {array}  actions is an array of actions
     * @return {promise} then a an object with keys as the actions, and bool
     * values
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

    /**
     * gets all available actions
     * @return {promise} then an array of actions
     */
    auth_factory.get_actions = () => $http.get(urls.accounts.get_actions).then((response) => response.data);

    return auth_factory;
  }
]);
