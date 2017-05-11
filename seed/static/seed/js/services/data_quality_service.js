/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// data_quality services
angular.module('BE.seed.service.data_quality', []).factory('data_quality_service', [
  '$http',
  function ($http) {
    var data_quality_factory = {};

    /*
     * get_data_quality_results
     * return data_quality results.
     * @param import_file_id: int, represents file import id.
     */
    data_quality_factory.get_data_quality_results = function (import_file_id) {
      return $http.get('/api/v2/import_files/' + import_file_id + '/data_quality_results').then(function (response) {
        return response.data.data;
      });
    };

    /**
     * gets the data quality rules for an org
     * @param  {int} org_id the id of the organization
     */
    data_quality_factory.data_quality_rules = function (org_id) {
      return $http.get('/api/v2/data_quality_checks/data_quality_rules/?organization_id=' + org_id).then(function (response) {
        return response.data;
      });
    };

    /**
     * resets default data data_quality rules for an org and destroys custom rules
     * @param  {int} org_id the id of the organization
     */
    data_quality_factory.reset_all_data_quality_rules = function (org_id) {
      return $http.put('/api/v2/data_quality_checks/reset_all_data_quality_rules/?organization_id=' + org_id).then(function (response) {
        return response.data;
      });
    };

    /**
     * resets default data data_quality rules for an org
     * @param  {int} org_id the id of the organization
     */
    data_quality_factory.reset_default_data_quality_rules = function (org_id) {
      return $http.put('/api/v2/data_quality_checks/reset_default_data_quality_rules/?organization_id=' + org_id).then(function (response) {
        return response.data;
      });
    };

    /**
     * saves the organization data data_quality rules
     * @param  {int} org_id the id of the organization
     * @param  {obj} data_quality_rules the updated rules to save
     */
    data_quality_factory.save_data_quality_rules = function (org_id, data_quality_rules) {
      return $http.post('/api/v2/data_quality_checks/save_data_quality_rules/?organization_id=' + org_id, {
        data_quality_rules: data_quality_rules
      }).then(function (response) {
        return response.data;
      });
    };

    data_quality_factory.start_data_quality_rules = function (org_id, property_state_ids, taxlot_state_ids) {
      return $http.post('/api/v2/data_quality_checks/?organization_id=' + org_id, {
        property_state_ids: property_state_ids,
        taxlot_state_ids: taxlot_state_ids
      }).then(function (response) {
        return response.data;
      });
    };

    data_quality_factory.start_data_quality_rules = function (org_id, task_id) {
      return $http.post('/api/v2/data_quality_checks/status/?organization_id=' + org_id, {
        task_id: task_id
      }).then(function (response) {
        return response.data;
      });
    };

    return data_quality_factory;
  }]);
