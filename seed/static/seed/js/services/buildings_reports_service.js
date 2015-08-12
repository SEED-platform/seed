
angular.module('BE.seed.service.buildings_reports', 
    []).factory('buildings_reports_service', [  '$http',
                                                '$q',
                                                '$timeout',
                                                'user_service',
                                    function (  $http, 
                                                $q, 
                                                $timeout, 
                                                user_service) {

   

    function get_report_data(xVar, yVar) {
        var defer = $q.defer();
        $http({
                method: 'GET',
                'url': window.BE.urls.get_building_report_data,
                'params': {
                    'organization_id': user_service.get_organization().id,
                    'xVar': xVar,
                    'yVar': yVar
                }
        }).success(function(data, status, headers, config) {
            building_reports_factory.report_data = (data != undefined && data.report_data != undefined) ? data.report_data : [];
            defer.resolve(data.report_data);
        }).error(function(data, status, headers, config) {
            building_reports_factory.reports_data = [];
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /* Public API */

    var building_reports_factory = { 
        
        //properties
        reports_data : [],

        //functions
        get_report_data : get_report_data        
    
    };

    return building_reports_factory;

}]);
