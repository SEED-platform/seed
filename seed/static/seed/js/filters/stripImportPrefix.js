/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * filter 'stripImportPrefix' for custom parsing of building 
 * ontology items like year built
 */
angular.module('stripImportPrefix', []).filter('stripImportPrefix', [
  '$filter',
  function($filter) {
    /** ids are sometime prefixed by the Import Record id.
    * e.g. import 28 would prefix all assessor data ids with 'IMP28-' and 
    *      stripImportPrefix would strip out the 'IMP28-'s from the html and only
    *      display the ids. 
    *
    * Usage: building.id = "IMP12-007"
    *        HTML: <span> {{ building.id | stripImportPrefix }} </span>
    *         compiles to: <span> 007 </span>
    *        JS  : stripImportPrefix(building.id)
    *         returns: "007"
    */
    return function(input) {
        if (typeof input === 'undefined' || input === null) {
            return input;
        }
        input = input.toString();
        var matches = input.match(/IMP\d+-(.+)/);
        if (matches) {
            // matches would be ["IMPxxx-yyyy", "yyyy"]
            return matches[1];
        }

        return input;

    };
}]);
