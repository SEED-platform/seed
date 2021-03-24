/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
