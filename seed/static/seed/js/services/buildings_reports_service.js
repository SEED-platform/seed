
angular.module('BE.seed.service.buildings_reports', 
    []).factory('buildings_reports_service', [  '$http',
                                                '$q',
                                                '$timeout',
                                                'user_service',
                                    function (  $http, 
                                                $q, 
                                                $timeout, 
                                                user_service) {

    var building_reports_factory = { reports_data : []};

    building_reports_factory.get_reports_data = function() {
        var defer = $q.defer();
        $http({
            method: 'GET',
            'url': window.BE.urls.get_building_reports_data,
            'params': {
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            reports_factory.reports_data = (data != undefined) ? data : [];
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            reports_factory.reports_data = [];
            defer.reject(data, status);
        });
        return defer.promise;
    };

    return building_reports_factory;

}]);
