/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.inventory_reports',
  []).factory('inventory_reports_service', [
  '$http',
  '$log',
  'user_service',
  function ($http,
            $log,
            user_service) {


    /**
     * Get inventory data given the provided parameters.
     Data will be passed back to caller as well as stored as a property
     of this service for other views that might want to bind to it.

     Response object will be in the format:
     {
       "status": "(success or error)",
       "data": {
         "chart_data": [
           {
             "id" the property (not state) id of the building,
             "yr_e" : the year ending value for this data point
             "x": value for x var,
             "y": value for y var,
           }...
         ],
         "property_counts": [
           {
             "yr_e": string for year ending
             "num_buildings": number of buildings in query results
             "num_buildings_w_data" : number of buildings with valid
                                      x and y data in query results
           }, ...
         ]
     }
 */
    function get_report_data(xVar, yVar, start, end) {

      // Error checks (should be able to collapse this...)
      if (_.isNil(xVar)) {
        $log.error('#inventory_reports_service.get_report_data(): null \'xVar\' parameter');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(yVar)) {
        $log.error('#inventory_reports_service.get_report_data(): null \'yVar\' parameter');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(start)) {
        $log.error('#inventory_reports_service.get_report_data(): null \'start\' parameter');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(end)) {
        $log.error('#inventory_reports_service.get_report_data(): null \'end\' parameter');
        throw new Error('Invalid Parameter');
      }

      return $http.get(window.BE.urls.get_inventory_report_data, {
        params: {
          organization_id: user_service.get_organization().id,
          x_var: xVar,
          y_var: yVar,
          start: start,
          end: end
        }
      }).then(function (response) {
        building_reports_factory.report_data = _.has(response.data, 'report_data') ? response.data.report_data : [];
        return response.data;
      }).catch(function () {
        building_reports_factory.reports_data = [];
      });
    }


    /**
     Get aggregated property data given the provided parameters.
     Data will be passed back to caller as well as stored as a property of
     this service for other views that might want to bind to it.

     Response object will be in the format:
     {
       "status": "(success or error)",
       "aggregated_data": {
         "chart_data": [
           {
             "x": value for x var,
             "y": value for secondary grouping
                   (e.g. '1990-1999' for decade when getting data
                   where y_var = year_built),
           },
           ...
         ],
         "property_counts": [
           {
             "yr_e": string for year ending - group by
             "num_buildings": number of buildings in query results
             "num_buildings_w_data" : number of buildings with valid
                                      x and y data in this group.
           },
          ...
       }
 */
    function get_aggregated_report_data(xVar, yVar, start, end) {

      // Error checks (should be able to collapse this...)
      if (_.isNil(xVar)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null \'xVar\' parameter');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(yVar)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null \'yVar\' parameter');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(start)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null \'start\' parameter');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(end)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null \'end\' parameter');
        throw new Error('Invalid Parameter');
      }

      return $http.get(window.BE.urls.get_aggregated_inventory_report_data, {
        params: {
          organization_id: user_service.get_organization().id,
          x_var: xVar,
          y_var: yVar,
          start: start,
          end: end
        }
      }).then(function (response) {
        building_reports_factory.aggregated_reports_data = _.has(response.data, 'report_data') ? response.data.report_data : [];
        return response.data;
      }).catch(function () {
        building_reports_factory.aggregated_reports_data = [];
      });
    }

    /*  This method is not currently used in the first version of the building reports page.
     Uncomment this method when the back end endpoint has been implemented.

     2016-09-06 Note this was never properly implemented in the old
     version so there is nothing meaningful to base the implementation
     on. Therefore the endpoint may never get implemented.
     */
    function get_summary_data(xVar, yVar, startDate, endDate) {
      return $http.get(window.BE.urls.get_inventory_summary_report_data, {
        params: {
          organization_id: user_service.get_organization().id,
          start_date: getDateString(startDate),
          end_date: getDateString(endDate)
        }
      }).then(function (response) {
        building_reports_factory.summary_data = _.has(response.data, 'summary_data') ? response.data.summary_data : [];
        return response.data;
      }).catch(function () {
        building_reports_factory.summary_data = [];
      });
    }

    /* Public API */

    var building_reports_factory = {

      //properties
      reports_data: [],
      aggregated_reports_data: [],
      summary_data: [],

      //functions
      //get_summary_data : get_summary_data,
      get_report_data: get_report_data,
      get_aggregated_report_data: get_aggregated_report_data

    };

    return building_reports_factory;

  }]);
