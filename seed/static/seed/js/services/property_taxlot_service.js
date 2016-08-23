/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// building services
angular.module('BE.seed.service.property_taxlot', []).factory('property_taxlot_service', [
  '$http',
  '$q',
  '$log',
  'urls',
  'user_service',
  'spinner_utility',
  function ($http, $q, $log, urls, user_service, spinner_utility) {

    var property_taxlot_service = { total_properties_for_user: 0,
                                    total_taxlots_for_user: 0};


    property_taxlot_service.get_properties = function (page, per_page, cycle) {

      var params = {
        organization_id: user_service.get_organization().id,
        page: page,
        per_page: per_page || 999999999
      };

      var lastCycleId = property_taxlot_service.get_last_cycle();
      if (cycle) {
        params.cycle = cycle.pk;
        property_taxlot_service.save_last_cycle(cycle.pk);
      } else if (_.isInteger(lastCycleId)) {
        params.cycle = lastCycleId;
      }

      var get_properties_url = "/app/properties";

      spinner_utility.show();
      var defer = $q.defer();
      $http({
        method: 'GET',
        url: get_properties_url,
        params: params
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);
      }).finally(function(){
        spinner_utility.hide();
      });
      return defer.promise;
    };


    /** Get Property information from server for a specified Property and Cycle and Organization.
     *
     *  @param property_id         The id of the requested Property
     *  @param cycle_id            The id of the requested Cycle for the requested Property
     *
     *  @returns {Promise}
     *
     *  The returned Property object (if the promise resolves successfully) will have a 'state' key with
     *  object containing all key/values for Property State (including 'extra_data')
     *  and a 'cycle' key with an object with at least the "id" key for that Cycle.
     *
     *  An example of structure of the returned JSON is...
     *
     *  {
     *    'property' {
     *      'id': 4,
     *      ..other Property fields...
     *     },
     *    'cycle': {
     *      'id': 1,
     *      ...other Cycle fields...
     *     },
     *     'taxlots': [
     *      ...array of objects with related TaxLot information...
     *     ],
     *     'state': {
     *        ...various key/values for Property state...
     *        extra_data : {
     *          ..various key/values for extra data...
     *        }
     *     }
     *     'changed_fields': {
     *        'regular_fields' : [
     *          ..list of keys for regular fields that have changed since last state
     *         ],
     *        'extra_data_fields' : [
     *          ..list of keys for extra_data fields that have changed since last state
     *         ]
     *      },
     *     'history' : [
     *        {
     *          'state': {
     *            ...various key/values for Property state...
     *              extra_data : {
     *                ..various key/values for extra data...
     *              }
     *           },
     *           'changed_fields': {
     *               'regular_fields' : [
     *                  ..list of keys for regular fields that have changed since last state
     *                ],
     *                'extra_data_fields' : [
     *                  ..list of keys for extra_data fields that have changed since last state
     *                ]
     *           },
     *           'date_edited': '2016-07-26T15:55:10.180Z'
     *           'source' : source of edit (ImportFile or UserEdit)
     *           'filename' : name of file if source=ImportFile
     *        },
     *        ... more history state objects...
     *     ]
     *     'status' : ('success' or 'error')
     *     'message' : (error message or empty string)
     *  }
     *
     */

    property_taxlot_service.get_property = function(property_id, cycle_id) {

      // Error checks
      if (angular.isUndefined(property_id)){
        $log.error("#property_taxlot_service.get_property(): property_id is undefined");
        throw new Error("Invalid Parameter");
      }
      if (angular.isUndefined(cycle_id)){
        $log.error("#property_taxlot_service.get_property(): cycle_id : is undefined");
        throw new Error("Invalid Parameter");
      }

      var defer = $q.defer();
      var organization_id = user_service.get_organization().id;
      var get_property_url = "/app/properties/" + property_id + "/cycles/" + cycle_id;

      spinner_utility.show();
      $http({
          method: 'GET',
          url: get_property_url,
          params: {
              organization_id: organization_id
          }
      }).success(function(data, status, headers, config) {
        defer.resolve(data);
      }).error(function(data, status, headers, config) {
        defer.reject(data, status);
      }).finally(function(){
        spinner_utility.hide();
      });
      return defer.promise;
    };

    /** Update Property State on server for a specified Property, Cycle and Organization.
     *
     * @param property_id         Property ID of the property
     * @param cycle_id            Cycle ID for the cycle
     * @param property_state      A Property state object, which should include key/values for
     *                              all state values
     *
     * @returns {Promise}
     */
    property_taxlot_service.update_property = function(property_id, cycle_id, property_state) {

        // Error checks
        if (angular.isUndefined(taxlot_id)){
          $log.error("#property_taxlot_service.get_taxlot(): property_id is undefined");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(cycle_id)){
          $log.error("#property_taxlot_service.get_taxlot(): null cycle_id is undefined");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(property_state)){
          $log.error("#property_taxlot_service.update_property(): 'property_state' is undefined");
          throw new Error("Invalid Parameter");
        }

        var defer = $q.defer();
        var organization_id = user_service.get_organization().id;
        var update_property_url = "/app/properties/" + String(property_id) + "/cycles/" + String(cycle_id);

        spinner_utility.show();
        $http({
            method: 'PUT',
            url: update_property_url,
            data: {
                organization_id: organization_id,
                state: property_state,
            },
        }).success(function(data, status, headers, config){
          defer.resolve(data);
        }).error(function(data, status, headers, config){
          defer.reject(data, status);
        }).finally(function(){
          spinner_utility.hide();
        });
        return defer.promise;
    };


		property_taxlot_service.delete_properties = function(search_payload) {

        var defer = $q.defer();
        var delete_properties_url = "/app/properties"
        var organization_id = user_service.get_organization().id

        spinner_utility.show();
        $http({
            method: 'DELETE',
            url: delete_properties_url,
            data: {
                organization_id: organization_id,
                search_payload: search_payload
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        }).finally(function(){
          spinner_utility.hide();
        });
        return defer.promise;
    };


    property_taxlot_service.get_taxlots = function (page, per_page, cycle) {

      var params = {
        organization_id: user_service.get_organization().id,
        page: page,
        per_page: per_page || 999999999
      };

      var lastCycleId = property_taxlot_service.get_last_cycle();

      if (cycle) {
        params.cycle = cycle.pk;
        property_taxlot_service.save_last_cycle(cycle.pk);
      } else if (_.isInteger(lastCycleId)) {
        params.cycle = lastCycleId;
      }

      var defer = $q.defer();
      var get_taxlots_url = "/app/taxlots";

      spinner_utility.show();
      $http({
        method: 'GET',
        url: get_taxlots_url,
        params: params
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);
      }).finally(function(){
        spinner_utility.hide();
      });
      return defer.promise;
    };





    /** Get TaxLot information from server for a specified TaxLot and Cycle and Organization.
     *
     *
     * @param taxlot_id         The id of the TaxLot object to retrieve
     * @param cycle_id          The id of the particular cycle for the requested TaxLot
     *
     * @returns {Promise}
     *
     * The returned TaxLot object (if the promise resolves successfully) will have a 'state' key with
     * object containing all key/values for TaxLot State (including 'extra_data')
     * and a 'cycle' key with an object with at least the "id" key for that Cycle.
     *
     *
     *  An example of structure of the returned JSON is...
     *
     *  {
     *    'taxlot' {
     *      'id': 4,
     *      ..other Property fields...
     *     },
     *    'cycle': {
     *      'id': 1,
     *      ...other Cycle fields...
     *     },
     *     'properties': [
     *      ...array of objects with related Property information...
     *     ],
     *     'state': {
     *        ...various key/values for TaxLot state...
     *        extra_data : {
     *          ..various key/values for extra data...
     *        }
     *     }
     *     'changed_fields': {
     *        'regular_fields' : [
     *          ..list of keys for regular fields that have changed since last state
     *         ],
     *        'extra_data_fields' : [
     *          ..list of keys for extra_data fields that have changed since last state
     *         ]
     *      },
     *     'history' : [
     *        {
     *          'state': {
     *              ...various key/values for TaxLot state...
     *              extra_data : {
     *                ..various key/values for extra data...
     *              }
     *           },
     *           'changed_fields': {
     *               'regular_fields' : [
     *                  ..list of keys for regular fields that have changed since last state
     *                ],
     *                'extra_data_fields' : [
     *                  ..list of keys for extra_data fields that have changed since last state
     *                ]
     *           },
     *           'date_edited': '2016-07-26T15:55:10.180Z'
     *           'source' : source of edit (ImportFile or UserEdit)
     *           'filename' : name of file if source=ImportFile
     *        },
     *        ... more history state objects...
     *     ]
     *     'status' : ('success' or 'error')
     *     'message' : (error message or empty string)
     *  }
     *
     */


    property_taxlot_service.get_taxlot = function(taxlot_id, cycle_id) {

      // Error checks
      if (angular.isUndefined(taxlot_id)){
        $log.error("#property_taxlot_service.get_taxlot(): null taxlot_id parameter");
        throw new Error("Invalid Parameter");
      }
      if (angular.isUndefined(cycle_id)){
        $log.error("#property_taxlot_service.get_taxlot(): null cycle_id parameter");
        throw new Error("Invalid Parameter");
      }

      var defer = $q.defer();
      var get_taxlot_url = "/app/taxlots/" + String(taxlot_id) + "/cycles/" + String(cycle_id);

      spinner_utility.show();
      $http({
          method: 'GET',
          url: get_taxlot_url,
          params: {
              organization_id: user_service.get_organization().id
          }
      }).success(function(data, status, headers, config) {
        defer.resolve(data);
      }).error(function(data, status, headers, config) {
        defer.reject(data, status);
      }).finally(function(){
        spinner_utility.hide();
      });
      return defer.promise;
    };



     /** Save TaxLot State for a specified Property and Cycle and Organization.
     *
     * @param taxlot_id           A Property object, which should include
     * @param cycle_id            A Property object, which should include
     * @param taxlot              A TaxLot State object, which should include key/values for
     *                            all TaxLot State properties
     *
     * @returns {Promise}
     */
    property_taxlot_service.update_taxlot = function(taxlot_id, cycle_id, taxlot_state) {

        // Error checks
        if (angular.isUndefined(taxlot_id)){
          $log.error("#property_taxlot_service.update_taxlot(): null taxlot_id parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(cycle_id)){
          $log.error("#property_taxlot_service.update_taxlot(): null cycle_id parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(organization_id)){
          $log.error("#property_taxlot_service.update_taxlot(): null organization_id parameter");
          throw new Error("Invalid Parameter");
        }
        if (angular.isUndefined(taxlot_state)){
          $log.error("#property_taxlot_service.update_taxlot(): null 'taxlot_state' parameter");
          throw new Error("Invalid Parameter");
        }

        var defer = $q.defer();
        var update_taxlot_url = "/app/properties/" + String(taxlot_id) + "/cycles/" + String(cycle_id);
        var organization_id = user_service.get_organization().id;

        spinner_utility.show();
        $http({
            method: 'PUT',
            url: update_taxlot_url,
            data: {
                organization_id: organization_id,
                state: taxlot_state,
            },
        }).success(function(data, status, headers, config){
          defer.resolve(data);
        }).error(function(data, status, headers, config){
          defer.reject(data, status);
        }).finally(function(){
          spinner_utility.hide();
        });
        return defer.promise;
    };



    property_taxlot_service.get_cycles = function () {

      var defer = $q.defer();
      var get_cycles_url = "/app/cycles";

      $http({
        method: 'GET',
        url: get_cycles_url,
        params: {
          organization_id: user_service.get_organization().id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);
      });
      return defer.promise;
    };

    property_taxlot_service.get_last_cycle = function () {
      var organization_id = user_service.get_organization().id,
        pk = (JSON.parse(sessionStorage.getItem('cycles')) || {})[organization_id];
      return pk;
    };

    property_taxlot_service.save_last_cycle = function (pk) {
      var organization_id = user_service.get_organization().id,
        cycles = JSON.parse(sessionStorage.getItem('cycles')) || {};
      cycles[organization_id] = _.toInteger(pk);
      sessionStorage.setItem('cycles', JSON.stringify(cycles));
    };


    property_taxlot_service.get_property_columns = function () {

      var defer = $q.defer();
      var get_property_columns_url = "/app/property-columns";
      var organization_id = user_service.get_organization().id;

      $http({
        method: 'GET',
        url: get_property_columns_url,
        params: {
          organization_id: organization_id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);
      });
      return defer.promise;
    };


    property_taxlot_service.get_taxlot_columns = function () {

      var defer = $q.defer();
      var get_taxlot_columns_url = "/app/taxlot-columns";
      var organization_id = user_service.get_organization().id;

      $http({
        method: 'GET',
        url: get_taxlot_columns_url,
        params: {
          organization_id: organization_id
        }
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);
      });
      return defer.promise;
    };

    var textRegex = /^(!?)"(([^"]|\\")*)"$/;
    property_taxlot_service.textFilter = function () {
      return {
        condition: function (searchTerm, cellValue) {
          if (_.isNil(cellValue)) cellValue = '';
          var filterData = searchTerm.match(textRegex);
          var regex;
          if (filterData) {
            var inverse = filterData[1] == '!';
            var value = filterData[2];
            regex = new RegExp('^' + _.escapeRegExp(value) + '$');
            return inverse ? !regex.test(cellValue) : regex.test(cellValue);
          } else {
            regex = new RegExp(_.escapeRegExp(searchTerm), 'i');
            return regex.test(cellValue);
          }
        }
      };
    };


    var numRegex = /^(==?|!=?|<>)?\s*(null|-?\d+)|(<=?|>=?)\s*(-?\d+)$/;
    property_taxlot_service.numFilter = function () {
      return {
        condition: function (searchTerm, cellValue) {
          var match = true;
          var searchTerms = _.map(_.split(searchTerm, ','), _.trim);
          _.forEach(searchTerms, function (search) {
            var filterData = search.match(numRegex);
            if (filterData) {
              var operator, value;
              if (!_.isUndefined(filterData[2])) {
                // Equality condition
                operator = filterData[1];
                value = filterData[2];
                if (_.isUndefined(operator) || _.startsWith(operator, '=')) {
                  // Equal
                  match = (value == 'null') ? (_.isNil(cellValue)) : (cellValue == value);
                  return match;
                } else {
                  // Not equal
                  match = (value == 'null') ? (!_.isNil(cellValue)) : (cellValue != value);
                  return match;
                }
              } else {
                // Range condition
                if (_.isNil(cellValue)) {
                  match = false;
                  return match;
                }

                operator = filterData[3];
                value = Number(filterData[4]);
                switch (operator) {
                  case '<':
                    match = cellValue < value;
                    return match;
                  case '<=':
                    match = cellValue <= value;
                    return match;
                  case '>':
                    match = cellValue > value;
                    return match;
                  case '>=':
                    match = cellValue >= value;
                    return match;
                }
              }
            } else {
              match = false;
              return match;
            }
          });
          return match;
        }
      };
    };


    property_taxlot_service.aggregations = function () {
      return {
        sum: {
          aggregationFn: function (aggregation, fieldValue) {
            if (!_.has(aggregation, 'values')) aggregation.values = [fieldValue];
            else aggregation.values.push(fieldValue);
          },
          finalizerFn: function (aggregation) {
            var sum = _.sum(_.without(aggregation.values, undefined, null, ''));
            aggregation.value = sum ? sum : null;
          }
        },
        uniqueList: {
          aggregationFn: function (aggregation, fieldValue) {
            if (!_.has(aggregation, 'values')) aggregation.values = [fieldValue];
            else aggregation.values.push(fieldValue);
          },
          finalizerFn: function (aggregation) {
            aggregation.value = _.join(_.uniq(_.without(aggregation.values, undefined, null, '')), '; ');
          }
        }
      };
    };


    property_taxlot_service.get_total_properties_for_user = function() {
        // django uses request.user for user information
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: window.BE.urls.get_total_number_of_properties_for_user_url
        }).success(function(data, status, headers, config) {
            property_factory.total_properties_for_user = data.properties_count;
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };


    property_taxlot_service.get_total_taxlots_for_user = function() {
        // django uses request.user for user information
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: window.BE.urls.get_total_number_of_taxlots_for_user_url
        }).success(function(data, status, headers, config) {
            property_factory.total_taxlots_for_user = data.taxlots_count;
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };


    // A list of which fields have date values. This will be used by controller
    // to format date value correctly. Ideally at some point this should be gathered
    // from the server rather than hardcoded here.

    // TODO: Identify Tax Lot specific values that have dates.
    var property_state_date_columns = [ "generation_date",
                                        "release_date",
                                        "recent_sale_date",
                                        "year_ending",
                                        "modified",
                                        "created"]

    property_taxlot_service.property_state_date_columns = property_state_date_columns;

    // TODO: Identify Tax Lot specific values that have dates.
    var property_state_date_columns = [ "generation_date",
                                        "release_date",
                                        "recent_sale_date",
                                        "year_ending",
                                        "modified",
                                        "created"]
    property_taxlot_service.taxlot_state_date_columns = property_state_date_columns;

    return property_taxlot_service;

  }]);
