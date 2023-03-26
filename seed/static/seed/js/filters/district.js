/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * district
 * For when you want to capitalize each word, remove underscores.
 */
angular.module('district', []).filter('district', function () {

  return function (input) {
    if (_.isNil(input)) {
      return input;
    }
    if (input.toUpperCase() === 'DISTRICT') {
      return 'County/District/Ward/Borough';
    }
    return input;
  };

});
