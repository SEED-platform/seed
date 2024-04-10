/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('sdUbid', []).directive('ubid', () => ({
  require: 'ngModel',
  link: (scope, elm, attrs, ctrl) => {
    ctrl.$validators.ubid = (modelValue) => UniqueBuildingIdentification.v3.isValid(modelValue);
  }
}));
