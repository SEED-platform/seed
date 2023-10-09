/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * StartFrom
 * For when you want to paginate client side, and start ng-repeat from a specific number.
 */
angular.module('startFrom', []).filter(
  'startFrom',
  // eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
  function () {
    return (input, start) => {
      start = +start; // parse to int
      return input.slice(start);
    };
  }
);
