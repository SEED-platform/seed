/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.inventory_reports', []).factory('inventory_reports_service', [
  '$http',
  '$log',
  'user_service',
  ($http, $log, user_service) => {
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
    const get_report_data = (xVar, yVar, cycle_ids, access_level_instance_id, filter_group_id) => {
      // Error checks
      if (_.some([xVar, yVar, cycle_ids], _.isNil)) {
        $log.error('#inventory_reports_service.get_report_data(): null parameter');
        throw new Error('Invalid Parameter');
      }

      const organization_id = user_service.get_organization().id;
      return $http
        .get(`/api/v3/organizations/${organization_id}/report/`, {
          params: {
            x_var: xVar,
            y_var: yVar,
            access_level_instance_id,
            cycle_ids,
            filter_group_id
          }
        })
        .then((response) => response.data)
        .catch(() => {});
    };

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
    const get_aggregated_report_data = (xVar, yVar, cycle_ids, access_level_instance_id, filter_group_id) => {
      // Error checks
      if ([xVar, yVar, cycle_ids].includes(null)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null parameter');
        throw new Error('Invalid Parameter');
      }

      const organization_id = user_service.get_organization().id;
      return $http
        .get(`/api/v3/organizations/${organization_id}/report_aggregated/`, {
          params: {
            x_var: xVar,
            y_var: yVar,
            cycle_ids,
            access_level_instance_id,
            filter_group_id
          }
        })
        .then((response) => response.data)
        .catch(() => {});
    };

    const export_reports_data = (axes_data, cycle_ids, filter_group_id) => {
      const {
        xVar, xLabel, yVar, yLabel
      } = axes_data;
      // Error checks
      if ([xVar, xLabel, yVar, yLabel].includes(null)) {
        $log.error('#inventory_reports_service.get_aggregated_report_data(): null parameter');
        throw new Error('Invalid Parameter');
      }

      const organization_id = user_service.get_organization().id;
      return $http
        .get(`/api/v3/organizations/${organization_id}/report_export/`, {
          params: {
            x_var: xVar,
            x_label: xLabel,
            y_var: yVar,
            y_label: yLabel,
            cycle_ids,
            filter_group_id
          },
          responseType: 'arraybuffer'
        })
        .then((response) => response);
    };

    return {
      get_report_data,
      get_aggregated_report_data,
      export_reports_data
    };
  }
]);
