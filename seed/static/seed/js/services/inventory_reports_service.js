/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.inventory_reports',
    []).factory('inventory_reports_service', ['$http',
                                                '$q',
                                                '$log',
                                                '$timeout',
                                                'user_service',
                                    function ( $http,
                                                $q,
                                                $log,
                                                $timeout,
                                                user_service) {


    /**     Get inventory data given the provided parameters.
            Data will be passed back to caller as well as stored as a property of this service
            for other views that might want to bind to it.

            Response object will be in the format:
            {
                "status": "(success or error)",
                "chart_data": [
                    {
                        "id" the id of the building,
                        "yr_e" : the year ending value for this data point
                        "x": value for x var,
                        "y": value for y var,
                    },
                    ...
                ],
                "property_counts": [
                    {
                        "yr_e": string for year ending
                        "num_buildings": number of buildings in query results
                        "num_buildings_w_data" : number of buildings with valid x and y data in query results
                    },
                    ...
                ]
            }
    */
    function get_report_data(xVar, yVar, startCycleID, endCycleID) {

        // Error checks (should be able to collapse this...)
        if (angular.isUndefined(xVar)){
          $log.error("#inventory_reports_service.get_report_data(): null 'xVar' parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(yVar)){
          $log.error("#inventory_reports_service.get_report_data(): null 'yVar' parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(startCycleID)){
          $log.error("#inventory_reports_service.get_report_data(): null 'startCycleID' parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(endCycleID)){
          $log.error("#inventory_reports_service.get_report_data(): null 'endCycleID' parameter");
          throw new Error("Invalid Parameter");
        }

        var defer = $q.defer();
        var args = {
                        organization_id: user_service.get_organization().id,
                        x_var: xVar,
                        y_var: yVar,
                        start_cycle_id: startCycleID,
                        end_cycle_id: endCycleID
                    };
        $http({
                method: 'GET',
                url: window.BE.urls.get_inventory_report_data,
                params: args
        }).success(function(data, status, headers, config) {
            building_reports_factory.report_data = (data !== undefined && data.report_data !== undefined) ? data.report_data : [];
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            building_reports_factory.reports_data = [];
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /**     Get aggregated property data given the provided parameters.
            Data will be passed back to caller as well as stored as a property of this service
            for other views that might want to bind to it.

            Response object will be in the format:
            {
                "status": "(success or error)",
                "chart_data": [
                    {
                        "yr_e" : the year ending value for this group
                        "x": value for x var,
                        "y": value for secondary grouping (e.g. '1990-1999' for decade when getting data where y_var = year_built),
                    },
                    ...
                ],
                "property_counts": [
                    {
                        "yr_e": string for year ending - group by
                        "num_buildings": number of buildings in query results
                        "num_buildings_w_data" : number of buildings with valid x and y data in this group.
                    },
                    ...
                ]
            }
    */
    function get_aggregated_report_data(xVar, yVar, startCycleID, endCycleID) {

       // Error checks (should be able to collapse this...)
        if (angular.isUndefined(xVar)){
          $log.error("#inventory_reports_service.get_aggregated_report_data(): null 'xVar' parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(yVar)){
          $log.error("#inventory_reports_service.get_aggregated_report_data(): null 'yVar' parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(startCycleID)){
          $log.error("#inventory_reports_service.get_aggregated_report_data(): null 'startCycleID' parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(endCycleID)){
          $log.error("#inventory_reports_service.get_aggregated_report_data(): null 'endCycleID' parameter");
          throw new Error("Invalid Parameter");
        }


        var defer = $q.defer();
        var args = {
                        organization_id: user_service.get_organization().id,
                        x_var: xVar,
                        y_var: yVar,
                        start_cycle_id: startCycleID,
                        end_cycle_id: endCycleID
                    };
        $http({
                method: 'GET',
                url: window.BE.urls.get_aggregated_property_report_data,
                params: args
        }).success(function(data, status, headers, config) {
            building_reports_factory.aggregated_reports_data = (data !== undefined && data.report_data !== undefined) ? data.report_data : [];
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            building_reports_factory.aggregated_reports_data = [];
            defer.reject(data, status);
        });
        return defer.promise;
    }

    /*  This method is not current used in the first version of the building reports page.
        Uncomment this method when the back end endpoint ahas been implemented.*/
    /*
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
    */

    /* Public API */

    var building_reports_factory = {

        //properties
        reports_data : [],
        aggregated_reports_data: [],
        summary_data : [],

        //functions
        //get_summary_data : get_summary_data,
        get_report_data : get_report_data,
        get_aggregated_report_data: get_aggregated_report_data

    };

    return building_reports_factory;

}]);
