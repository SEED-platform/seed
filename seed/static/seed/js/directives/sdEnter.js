/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
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
