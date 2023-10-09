/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
angular.module('sdUbid', []).directive('ubid', function () {
  return {
    require: 'ngModel',
    link(scope, elm, attrs, ctrl) {
      ctrl.$validators.ubid = (modelValue) => UniqueBuildingIdentification.v3.isValid(modelValue);
    }
  };
});
