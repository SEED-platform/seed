/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
