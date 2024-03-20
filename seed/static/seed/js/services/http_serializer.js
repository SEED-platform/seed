/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 * :author 'Nicholas Serra <nickserra@gmail.com>, nicholasserra'
 *
 * Custom $http params serializer that url encodes semicolons.
 * Temporary until a fix is landed in angular.
 */
angular.module('BE.seed.service.httpParamSerializerSeed', []).factory('httpParamSerializerSeed', [
  () => {
    function serializeValue(v) {
      if (angular.isObject(v)) {
        return angular.isDate(v) ? v.toISOString() : angular.toJson(v);
      }
      return v;
    }

    function forEachSorted(obj, iterator, context) {
      const keys = Object.keys(obj).sort();
      for (let i = 0; i < keys.length; i++) {
        iterator.call(context, obj[keys[i]], keys[i]);
      }
      return keys;
    }

    const encodeUriQuerySeed = (val, pctEncodeSpaces) => encodeURIComponent(val)
      .replace(/%40/gi, '@')
      .replace(/%3A/gi, ':')
      .replace(/%24/g, '$')
      .replace(/%2C/gi, ',')
      .replace(/%20/g, pctEncodeSpaces ? '%20' : '+');

    return (params) => {
      if (!params) return '';
      const parts = [];
      forEachSorted(params, (value, key) => {
        if (value === null || angular.isUndefined(value)) return;
        if (angular.isArray(value)) {
          angular.forEach(value, (v) => {
            parts.push(`${encodeUriQuerySeed(key)}=${encodeUriQuerySeed(serializeValue(v))}`);
          });
        } else {
          parts.push(`${encodeUriQuerySeed(key)}=${encodeUriQuerySeed(serializeValue(value))}`);
        }
      });

      return parts.join('&');
    };
  }
]);
