/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('ignoremap', []).filter(
  'ignoremap',
  // eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
  function () {
    return (input) => {
      if (_.isEmpty(input)) return '------ Ignore Row ------';
      return input;
    };
  }
);
