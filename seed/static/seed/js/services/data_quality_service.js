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
      console.debug('Fetching ', '/api/v2/import_files/' + import_file_id + '/data_quality_results');
      return $http.get('/api/v2/import_files/' + import_file_id + '/data_quality_results').then(function (response) {
        return response.data.data;
      });
    };

    return data_quality_factory;
  }]);
