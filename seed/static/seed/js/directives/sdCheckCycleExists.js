/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('sdCheckCycleExists', []).directive('sdCheckCycleExists', () => ({
  require: 'ngModel',
  scope: {
    existingCycles: '=sdCheckCycleExists'
  },
  link: (scope, elm, attrs, ctrl) => {
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
}));
