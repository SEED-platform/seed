/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * filter 'fromNow' using the moment.js function 'fromNow()'
 * see: http://momentjs.com/
 */
angular.module('fromNow', []).filter('fromNow', function() {
    return function(dateString) {
        if (angular.isNumber(dateString)){
            return moment(dateString).fromNow();
        }
        return 'a few seconds ago';
    };
});
