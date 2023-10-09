/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
angular.module('sdCheckLabelExists', []).directive('sdCheckLabelExists', function () {
  return {
    require: 'ngModel',
    scope: {
      existingLabels: '=sdCheckLabelExists'
    },
    link(scope, elm, attrs, ctrl) {
      ctrl.$validators.sdCheckLabelExists = (modelValue) => {
        if (!modelValue) return true;

        const labels = scope.existingLabels;
        if (!labels) return true;

        const len = labels.length;
        for (let index = 0; index < len; index++) {
          const label = labels[index];
          if (label.name === modelValue) {
            return false;
          }
        }

        return true;
      };
    }
  };
});
