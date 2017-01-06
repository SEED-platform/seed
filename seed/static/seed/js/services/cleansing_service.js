/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// cleansing services
angular.module('BE.seed.service.cleansing', []).factory('cleansing_service', [
  '$http',
  function ($http) {
    var cleansing_factory = {};

    /*
     * get_cleansing_results
     * return cleansing results.
     * @param import_file_id: int, represents file import id.
     */
    cleansing_factory.get_cleansing_results = function (import_file_id) {
      return $http.get('/api/v2/import_files/' + import_file_id + '/cleansing_results.json').then(function (response) {
        return response.data.data;
      });
    };

    return cleansing_factory;
  }]);
