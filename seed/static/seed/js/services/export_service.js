/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// dataset services
angular.module('BE.seed.service.export', []).factory('export_service', [
  '$http',
  '$q',
  function ($http, $q) {
    var export_factpry = {};

    export_factpry.export_buildings = function(buildings_payload) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.export_buildings,
            'data': buildings_payload
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };
    export_factpry.export_buildings_progress = function(export_id) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.export_buildings_progress,
            'data': {'export_id': export_id}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };
    export_factpry.export_buildings_download = function(export_id) {
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.export_buildings_download,
            'data': {'export_id': export_id}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    return export_factpry;
}]);
