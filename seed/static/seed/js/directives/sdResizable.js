/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
(function () {
  'use strict';

  angular
    .module('sdResizable', [])
    .directive('sdResizable', resizable);

  /**
   * angular directive to wrap jQuery's resizable functionality
   */
  function resizable () {
    var resizableConfig = {
      handles: 'e',
      alsoResize: 'table.resizable'
    };

    return {
      restrict: 'A',
      scope: {
        callback: '&onResize'
      },
      link: function postLink (scope, elem) {
        elem.resizable(resizableConfig);
        elem.css('position', 'relative');
        elem.on('resizestop', function () {
          if (scope.callback) scope.callback();
        });
        elem.on('resize', function (event, ui) {
          elem.css('minWidth', ui.size.width + 'px');
        });
        // keeping this here for when we are ready to add in the double-click
        /*elem.on('dblclick', function(e) {
         console.log('dbl-clicked, elem: ' + elem + ', e: ' + e);
         });*/
      }
    };
  }
})();
