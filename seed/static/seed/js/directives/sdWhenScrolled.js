/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * infinite-scrolling: http://jsfiddle.net/vojtajina/U7Bz9/
 */
angular.module('sdWhenScrolled', []).directive(
  'sdWhenScrolled',
  () => (scope, elm, attr) => {
    const raw = elm[0];

    elm.bind('scroll', () => {
      if (raw.scrollTop + raw.offsetHeight >= raw.scrollHeight) {
        scope.$apply(attr.sdWhenScrolled);
      }
    });
  }
);
