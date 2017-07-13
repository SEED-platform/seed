/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * StartFrom
 * For when you want to paginate client side, and start ng-repeat from a specific number.
 */
angular.module('startFrom', []).filter('startFrom', function () {

  return function (input, start) {
    start = +start; // parse to int
    return input.slice(start);
  };

});
