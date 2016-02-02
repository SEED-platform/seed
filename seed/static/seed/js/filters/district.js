/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/*
 * district
 * For when you want to capitalize each word, remove underscores.
 */
angular.module('district', []).filter('district', [
  '$filter',
  function($filter) {

    return function(input) {
        if (typeof input === 'undefined' || input === null) {
            return input;
        }
        if (angular.uppercase(input) === 'DISTRICT'){
            return "County/District/Ward/Borough";
        }
        return input;
    };

}]);
