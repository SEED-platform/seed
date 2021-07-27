/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author 'Nicholas Serra <nickserra@gmail.com>'
 */
/**
 *
 * Custom $http params serializer that url encodes semicolons.
 * Temporary until a fix is landed in angular.
 * - nicholasserra
 */
angular.module('BE.seed.service.httpParamSerializerSeed', []).factory('httpParamSerializerSeed', [
  function () {

    function serializeValue (v) {
      if (angular.isObject(v)) {
        return angular.isDate(v) ? v.toISOString() : angular.toJson(v);
      }
      return v;
    }

    function forEachSorted (obj, iterator, context) {
      var keys = Object.keys(obj).sort();
      for (var i = 0; i < keys.length; i++) {
        iterator.call(context, obj[keys[i]], keys[i]);
      }
      return keys;
    }

    function encodeUriQuerySeed (val, pctEncodeSpaces) {
      return encodeURIComponent(val).
        replace(/%40/gi, '@').
        replace(/%3A/gi, ':').
        replace(/%24/g, '$').
        replace(/%2C/gi, ',').
        replace(/%20/g, (pctEncodeSpaces ? '%20' : '+'));
    }

    return function (params) {
      if (!params) return '';
      var parts = [];
      forEachSorted(params, function (value, key) {
        if (value === null || angular.isUndefined(value)) return;
        if (angular.isArray(value)) {
          angular.forEach(value, function (v) {
            parts.push(encodeUriQuerySeed(key) + '=' + encodeUriQuerySeed(serializeValue(v)));
          });
        } else {
          parts.push(encodeUriQuerySeed(key) + '=' + encodeUriQuerySeed(serializeValue(value)));
        }
      });

      return parts.join('&');
    };
  }]);
