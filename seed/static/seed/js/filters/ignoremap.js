/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('ignoremap', []).filter('ignoremap', function () {
  return function (input) {
    if (_.isEmpty(input)) return '------ Ignore Row ------';
    return input;
  };

});
