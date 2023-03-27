/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('sdCheckCycleExists', []).directive('sdCheckCycleExists', function () {
  return {
    require: 'ngModel',
    scope: {
      existingCycles: '=sdCheckCycleExists'
    },
    link: function (scope, elm, attrs, ctrl) {

      ctrl.$validators.sdCheckCycleExists = function (modelValue) {

        if(!modelValue) return true;

        var cycles = scope.existingCycles;
        if (!cycles) return true;

        var len = cycles.length;
        for (var index = 0; index < len; index++) {
          var cycle = cycles[index];
          if (cycle.name === modelValue) {
            return false;
          }
        }

        return true;

      };
    }
  };
});
