
angular.module('BE.seed.service.buildings_reports', 
    []).factory('buildings_reports_service', [  '$http',
                                                '$q',
                                                '$timeout',
                                                'user_service',
                                    function (  $http, 
                                                $q, 
                                                $timeout, 
                                                user_service) {

   
    function get_summary_data(xVar, yVar, startDate, endDate) {
        var defer = $q.defer();

        var args = {
                        organization_id: user_service.get_organization().id,     
                        start_date: getDateString(startDate),
                        end_date: getDateString(endDate)
                    };
       
        $http({
                method: 'GET',
                'url': window.BE.urls.get_building_summary_report_data,
                'params': args
        }).success(function(data, status, headers, config) {
            building_reports_factory.summary_data = (data != undefined && data.summary_data != undefined) ? data.summary_data : [];
            defer.resolve(data.summary_data);
        }).error(function(data, status, headers, config) {
            building_reports_factory.summary_data = [];
            defer.reject(data, status);
        });
        return defer.promise;
    };

    function get_report_data(xVar, yVar, startDate, endDate) {
        var defer = $q.defer();
        var args = {
                        organization_id: user_service.get_organization().id,
                        x_var: xVar,
                        y_var: yVar,
                        start_date: getDateString(startDate),
                        end_date: getDateString(endDate)
                    };
        $http({
                method: 'GET',
                url: window.BE.urls.get_building_report_data,
                params: args
        }).success(function(data, status, headers, config) {
            building_reports_factory.report_data = (data != undefined && data.report_data != undefined) ? data.report_data : [];
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            building_reports_factory.reports_data = [];
            defer.reject(data, status);
        });
        return defer.promise;
    };


    function get_aggregated_report_data(xVar, yVar, startDate, endDate) {
        var defer = $q.defer();
        var args = {
                        organization_id: user_service.get_organization().id,
                        x_var: xVar,
                        y_var: yVar,
                        start_date: getDateString(startDate),
                        end_date: getDateString(endDate)
                    };
        $http({
                method: 'GET',
                url: window.BE.urls.get_aggregated_building_report_data,
                params: args
        }).success(function(data, status, headers, config) {
            building_reports_factory.aggregated_reports_data = (data != undefined && data.report_data != undefined) ? data.report_data : [];
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            building_reports_factory.aggregated_reports_data = [];
            defer.reject(data, status);
        });
        return defer.promise;
    };

    function getDateString(dateObj){
       var yyyy = dateObj.getFullYear().toString();
       var mm = (dateObj.getMonth()+1).toString(); // getMonth() is zero-based
       var dd  = dateObj.getDate().toString();
       return yyyy + '-' + (mm[1]?mm:"0"+mm[0]) + '-' + (dd[1]?dd:"0"+dd[0]); // padding
    }

    /* Public API */

    var building_reports_factory = { 
        
        //properties
        reports_data : [],
        aggregated_reports_data: [],
        summary_data : [],

        //functions
        get_summary_data : get_summary_data,
        get_report_data : get_report_data,
        get_aggregated_report_data: get_aggregated_report_data    
    
    };

    return building_reports_factory;

}]);
