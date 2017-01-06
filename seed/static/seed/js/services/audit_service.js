/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// dataset services
angular.module('BE.seed.service.audit', []).factory('audit_service', [
  '$http',
  'user_service',
  'generated_urls',
  function ($http, user_service, generated_urls) {
    var audit_log_factory = {};

    /**
     * gets a list of audit_logs for a building
     * @param  {str or int} building_id building canonical id
     * @return {obj}             payload with key `audit_logs`
     */
    audit_log_factory.get_building_logs = function (building_id) {
      return $http.get(generated_urls.audit_logs.get_building_logs, {
        params: {
          organization_id: user_service.get_organization().id,
          building_id: building_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * creates a new note within the building's audit_log
     * @param  {str/int} building_id canonical id
     * @param  {str} action_note
     * @return {obj}             status obj
     */
    audit_log_factory.create_note = function (building_id, action_note) {
      return $http.post(generated_urls.audit_logs.create_note, {
        organization_id: user_service.get_organization().id,
        building_id: building_id,
        action_note: action_note
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * updates an existing note
     * @return {obj} status obj
     * @param  {str} action_note
     */
    audit_log_factory.update_note = function (audit_log_id, action_note) {
      return $http.put(generated_urls.audit_logs.update_note, {
        organization_id: user_service.get_organization().id,
        action_note: action_note,
        audit_log_id: audit_log_id
      }).then(function (response) {
        return response.data;
      });
    };

    return audit_log_factory;
  }]);
