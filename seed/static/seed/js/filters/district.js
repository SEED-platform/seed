/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
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
