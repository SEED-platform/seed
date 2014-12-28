/**
 * :copyright: (c) 2014 Building Energy Inc
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
