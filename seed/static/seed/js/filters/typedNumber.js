/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * filter 'typedNumber' for custom parsing of building 
 * ontology items like year built
 */
angular.module('typedNumber', []).filter('typedNumber', [
  '$filter',
  function($filter) {
    return function(input, column_type, column_name, fixed_digits) {
        if (input === 0 || isNaN(input)) {
            return input;
        }
        fixed_digits = fixed_digits || 0;
        column_type = column_type || "string";
        column_name = column_name || "";
        if (column_type === "string" || column_name === "year_built") {
            return input;
        }

        return $filter('number')(input, fixed_digits);

    };
}]);
