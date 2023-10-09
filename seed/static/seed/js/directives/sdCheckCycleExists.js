/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
angular.module('sdCheckCycleExists', []).directive('sdCheckCycleExists', function () {
  return {
    require: 'ngModel',
    scope: {
      existingCycles: '=sdCheckCycleExists'
    },
    link(scope, elm, attrs, ctrl) {
      ctrl.$validators.sdCheckCycleExists = (modelValue) => {
        if (!modelValue) return true;

        const cycles = scope.existingCycles;
        if (!cycles) return true;

        const len = cycles.length;
        for (let index = 0; index < len; index++) {
          const cycle = cycles[index];
          if (cycle.name === modelValue) {
            return false;
          }
        }

        return true;
      };
    }
  };
});
