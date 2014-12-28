/**
 * :copyright: (c) 2014 Building Energy Inc
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
