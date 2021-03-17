/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * directive sd-label: adds a bootstrap label from a color
 */
angular.module('sdLabel', []).directive('sdLabel', ['$log', function ($log) {
  return {
    scope: {},
    restrict: 'E',
    link: function (scope, element, attrs) {
      scope.name = attrs.name;
      var lookup_label = function (color) {
        var lookup_colors = {
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
  };
}]);
