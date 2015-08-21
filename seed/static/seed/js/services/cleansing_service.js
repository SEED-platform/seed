// cleansing services
angular.module('BE.seed.service.cleansing', []).factory('cleansing_service', [
  '$http',
  '$q',
  '$timeout',
  'user_service',
  function ($http, $q, $timeout, user_service) {
    var cleansing_factory = {};

    /*
     * get_cleansing_results
     * return cleansing results.
     * @param import_file_id: int, represents file import id.
     */
    cleansing_factory.get_cleansing_results = function(import_file_id) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            'url': '/cleansing/results/?import_file_id=' + import_file_id
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    return cleansing_factory;
}]);
