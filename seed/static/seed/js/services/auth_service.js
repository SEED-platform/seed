/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.service.auth', []).factory('auth_service', [
  '$http',
  '$q',
  'generated_urls',
  function ($http, $q, generated_urls) {

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
     * @param  {organization_id}  id of ogranization
     * @param  {array}  actions is an array of actions
     * @return {promise} then a an object with keys as the actions, and bool
     * values
     */
    auth_factory.is_authorized = function(organization_id, actions) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': urls.accounts.is_authorized,
            'data': {
                'actions': actions,
                'organization_id': organization_id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * gets all availble actions
     * @return {promise} then an array of actions
     */
    auth_factory.get_actions = function(user) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            'url': urls.accounts.get_actions
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    return auth_factory;
}]);
