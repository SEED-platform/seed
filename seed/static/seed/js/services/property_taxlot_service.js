/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// building services
angular.module('BE.seed.service.property_taxlot', []).factory('property_taxlot_service', [
  '$http',
  '$q',
  'urls',
  'user_service',
  'spinner_utility',
  function ($http, $q, urls, user_service, spinner_utility) {

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

      spinner_utility.show();
      var defer = $q.defer();
      $http({
        method: 'GET',
        url: window.BE.urls.get_properties,
        params: params
      }).success(function (data, status, headers, config) {
        spinner_utility.hide();
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        spinner_utility.hide();
        defer.reject(data, status);
      });
      return defer.promise;
    };



    property_taxlot_service.get_property = function(property_id, cycle_id) {

        var defer = $q.defer();

        spinner_utility.show();
        $http({
            method: 'GET',
            url: window.BE.urls.get_property,
            params: {
                property_id: property_id,
                cycle_id: cycle_id,
                organization_id: user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            spinner_utility.hide();
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            spinner_utility.hide();
            defer.reject(data, status);
        });
        return defer.promise;
    };


    property_taxlot_service.update_property = function(property, organization_id) {

        var defer = $q.defer();

        spinner_utility.show();
        $http({
            method: 'PUT',
            url: window.BE.urls.update_property,
            data: {
                property: property,
                organization_id: organization_id
            },
        }).success(function(data, status, headers, config){
          spinner_utility.hide();
          defer.resolve(data);
        }).error(function(data, status, headers, config){
          spinner_utility.hide();
          defer.reject(data, status);
        });
        return defer.promise;
    };


		property_taxlot_service.delete_properties = function(search_payload) {
        spinner_utility.show();
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            url: generated_urls.seed.delete_properties,
            data: {
                organization_id: user_service.get_organization().id,
                search_payload: search_payload
            }
        }).success(function(data, status, headers, config) {
            spinner_utility.hide();
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
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
      $http({
        method: 'GET',
        url: window.BE.urls.get_taxlots,
        params: params
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);
      });
      return defer.promise;
    };

    property_taxlot_service.get_cycles = function () {
      var defer = $q.defer();
      $http({
        method: 'GET',
        url: window.BE.urls.get_cycles,
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
      $http({
        method: 'GET',
        url: window.BE.urls.get_property_columns,
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

    property_taxlot_service.get_taxlot_columns = function () {
      var defer = $q.defer();
      $http({
        method: 'GET',
        url: window.BE.urls.get_taxlot_columns,
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

    return property_taxlot_service;
  }]);
