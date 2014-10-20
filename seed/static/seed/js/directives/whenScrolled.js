
/**
 * infinite-scrolling: http://jsfiddle.net/vojtajina/U7Bz9/
 */
angular.module('whenScrolled', []).directive('whenScrolled', function() {
    return function(scope, elm, attr) {
        var raw = elm[0];
        
        elm.bind('scroll', function() {
            if (raw.scrollTop + raw.offsetHeight >= raw.scrollHeight) {
                scope.$apply(attr.whenScrolled);
            }
        });
    };
});
