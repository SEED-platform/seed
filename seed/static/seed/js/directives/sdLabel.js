/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * directive sd-label: adds a bootstrap label from a color
 */
angular.module('sdLabel', []).directive('sdLabel', [
  '$log',
  ($log) => ({
    scope: {},
    restrict: 'E',
    link: (scope, element, attrs) => {
      scope.name = attrs.name;
      const lookup_label = (color) => {
        const lookup_colors = {
          red: 'danger',
          gray: 'default',
          grey: 'default',
          orange: 'warning',
          green: 'success',
          blue: 'primary',
          'light blue': 'info'
        };
        try {
          return lookup_colors[color];
        } catch (err) {
          $log.log(err);
          return lookup_colors.white;
        }
      };
      scope.label = lookup_label(attrs.color);
    },
    replace: true,
    template: '<span class="label label-{$ label $}">{$ name $}</span>'
  })
]);
