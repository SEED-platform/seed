/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * angular directive to wrap jQuery's resizable functionality
 */
// eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
angular.module('sdResizable', []).directive('sdResizable', function () {
  const resizableConfig = {
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
      elem.on('resizestop', () => {
        if (scope.callback) scope.callback();
      });
      elem.on('resize', (event, ui) => {
        elem.css('minWidth', `${ui.size.width}px`);
      });
      // keeping this here for when we are ready to add in the double-click
      /* elem.on('dblclick', function(e) {
       console.log('dbl-clicked, elem: ' + elem + ', e: ' + e);
       }); */
    }
  };
});
