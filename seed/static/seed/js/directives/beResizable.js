(function() {
    'use strict';

    angular
        .module('beResizable',[])
        .directive('beResizable', resizable);

    /**
     * angular directive to wrap jQuery's resizable functionality
    */
    function resizable() {
        var resizableConfig = {
            handles: 'e',
            alsoResize: 'table.resizable'
        };

        return {
            restrict: 'A',
            scope: {
                callback: '&onResize'
            },
            link: function postLink(scope, elem) {
                elem.resizable(resizableConfig);
                elem.css('position', 'relative');
                elem.on('resizestop', function () {
                    if (scope.callback) scope.callback();
                });
                // keeping this here for when we are ready to add in the double-click
                /*elem.on('dblclick', function(e) {
                 console.log('dbl-clicked, elem: ' + elem + ', e: ' + e);
                 });*/
            }
        };
    }
})();
