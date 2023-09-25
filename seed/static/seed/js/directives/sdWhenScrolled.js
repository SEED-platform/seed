/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * infinite-scrolling: http://jsfiddle.net/vojtajina/U7Bz9/
 */
angular.module('sdWhenScrolled', []).directive('sdWhenScrolled', function () {
  return function (scope, elm, attr) {
    var raw = elm[0];

    elm.bind('scroll', function () {
      if (raw.scrollTop + raw.offsetHeight >= raw.scrollHeight) {
        scope.$apply(attr.sdWhenScrolled);
      }
    });
  };
});
