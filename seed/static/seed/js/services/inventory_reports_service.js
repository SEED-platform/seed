/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.inventory_reports',
  []).factory('inventory_reports_service', [
  '$http',
  '$log',
  'user_service',
  function (
    $http,
    $log,
    user_service
  ) {


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
    function get_report_data (xVar, yVar, start, end) {

      // Error checks
      if (_.some([xVar, yVar, start, end], _.isNil)) {
        $log.error('#inventory_reports_service.get_report_data(): null parameter');
        throw new Error('Invalid Parameter');
      }

      const organization_id = user_service.get_organization().id;
      return $http.get('/api/v3/organizations/' + organization_id + '/report/', {
        params: {
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
         "chart_data": [{
           "x": value for x var,
           "y": value for secondary grouping
                (e.g., '1990-1999' for decade when getting data
                where y_var = year_built),
         }, {
           ...
         }],
         "property_counts": [{
           "yr_e": string for year ending - group by
           "num_buildings": number of buildings in query results
           "num_buildings_w_data": number of buildings with valid
                                   x and y data in this group.
         }, {
           ...
         }]
       }
     }
     */
    function get_aggregated_report_data (xVar, yVar, start, end) {

      // Error checks
      if (_.some([xVar, yVar, start, end], _.isNil)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null parameter');
        throw new Error('Invalid Parameter');
      }

      const organization_id = user_service.get_organization().id;
      return $http.get('/api/v3/organizations/' + organization_id + '/report_aggregated/', {
        params: {
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

    function export_reports_data (axes_data, start, end) {
      var xVar = axes_data.xVar;
      var xLabel = axes_data.xLabel;
      var yVar = axes_data.yVar;
      var yLabel = axes_data.yLabel;
      // Error checks
      if (_.some([xVar, xLabel, yVar, yLabel, start, end], _.isNil)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null parameter');
        throw new Error('Invalid Parameter');
      }

      const organization_id = user_service.get_organization().id;
      return $http.get('/api/v3/organizations/' + organization_id + '/report_export/', {
        params: {
          x_var: xVar,
          x_label: xLabel,
          y_var: yVar,
          y_label: yLabel,
          start: start,
          end: end
        },
        responseType: 'arraybuffer'
      }).then(function (response) {
        return response;
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
      get_aggregated_report_data: get_aggregated_report_data,
      export_reports_data: export_reports_data

    };

    return building_reports_factory;

  }]);
