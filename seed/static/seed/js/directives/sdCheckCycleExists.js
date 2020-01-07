/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
