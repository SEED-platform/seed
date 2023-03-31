/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * Directive sd-enter used for search or filter input to only fire on 'enter' or 'return'
 */
angular.module('sdEnter', []).directive('sdEnter', function () {
  return function (scope, element, attrs) {
    element.bind('keydown keypress', function (event) {
      if (event.which === 13) {
        scope.$apply(function () {
          scope.$eval(attrs.sdEnter);
        });
        event.preventDefault();
      }
    });
  };
});
