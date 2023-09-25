/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('sdCheckLabelExists', []).directive('sdCheckLabelExists', function () {
  return {
    require: 'ngModel',
    scope: {
      existingLabels: '=sdCheckLabelExists'
    },
    link: function (scope, elm, attrs, ctrl) {

      ctrl.$validators.sdCheckLabelExists = function (modelValue) {

        if(!modelValue) return true;

        var labels = scope.existingLabels;
        if (!labels) return true;

        var len = labels.length;
        for (var index = 0; index < len; index++) {
          var label = labels[index];
          if (label.name === modelValue) {
            return false;
          }
        }

        return true;

      };
    }
  };
});
