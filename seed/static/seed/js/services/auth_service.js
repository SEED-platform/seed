/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.auth', []).factory('auth_service', [
  '$http',
  'user_service',
  'generated_urls',
  function ($http, user_service, generated_urls) {

    var auth_factory = {};
    var urls = generated_urls;

    /**
     * checks against the auth backend to determine if the requesting user is
     * authorized for a given action. This should happen once per page view.
     *
     * e.g. from the route dispatcher:
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
    auth_factory.is_authorized = function (organization_id, actions) {
      return user_service.get_user_id().then(function (user_id) {
        return $http.post('/api/v3/users/' + user_id + '/is_authorized/', {
          actions: actions
        }, {
          params: {
            organization_id: organization_id
          }
        }).then(function (response) {
          return response.data;
        });
      });
    };

    /**
     * gets all available actions
     * @return {promise} then an array of actions
     */
    auth_factory.get_actions = function () {
      return $http.get(urls.accounts.get_actions).then(function (response) {
        return response.data;
      });
    };

    return auth_factory;
  }]);
