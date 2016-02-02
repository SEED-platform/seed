/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * infinite-scrolling: http://jsfiddle.net/vojtajina/U7Bz9/
 */
angular.module('sdWhenScrolled', []).directive('sdWhenScrolled', function() {
    return function(scope, elm, attr) {
        var raw = elm[0];
        
        elm.bind('scroll', function() {
            if (raw.scrollTop + raw.offsetHeight >= raw.scrollHeight) {
                scope.$apply(attr.sdWhenScrolled);
            }
        });
    };
});
