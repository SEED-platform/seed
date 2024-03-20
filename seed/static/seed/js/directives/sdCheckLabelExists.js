/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('sdCheckLabelExists', []).directive('sdCheckLabelExists', () => ({
  require: 'ngModel',
  scope: {
    existingLabels: '=sdCheckLabelExists'
  },
  link: (scope, elm, attrs, ctrl) => {
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
}));
