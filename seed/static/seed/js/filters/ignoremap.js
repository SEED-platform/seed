/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('ignoremap', []).filter('ignoremap', [
  '$filter',
  function($filter) {

    return function(input) {
        if (typeof input === 'undefined' || input === null || input === "") {
            return "------ Ignore Row ------";
        }
        return input;
    };

}]);
