/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// building services
angular.module('BE.seed.service.bluesky_service', []).factory('bluesky_service', [
  '$http',
  '$q',
  'urls',
  'user_service',
  function ($http, $q, urls, user_service) {
    var bluesky_service = {};

    bluesky_service.get_properties = function (page, per_page, cycle) {
      var params = {
        organization_id: user_service.get_organization().id,
        page: page,
        per_page: per_page || 999999999
      };

      if (cycle) {
        params.cycle = cycle.pk;
      }

      var defer = $q.defer();
      $http({
        method: 'GET',
        url: window.BE.urls.get_properties,
        params: params
      }).success(function (data, status, headers, config) {
        defer.resolve(data);
      }).error(function (data, status, headers, config) {
        defer.reject(data, status);
      });
      return defer.promise;
    };

    bluesky_service.get_taxlots = function (page, per_page, cycle) {
      var params = {
        organization_id: user_service.get_organization().id,
        page: page,
        per_page: per_page || 999999999
      };

      if (cycle) {
        params.cycle = cycle.pk;
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

    bluesky_service.get_cycles = function () {
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

    bluesky_service.get_property_columns = function () {
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

    bluesky_service.get_taxlot_columns = function () {
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
    bluesky_service.textFilter = function () {
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
    bluesky_service.numFilter = function () {
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

    bluesky_service.aggregations = function () {
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

    return bluesky_service;
  }]);
