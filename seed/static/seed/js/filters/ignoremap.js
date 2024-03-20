/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('ignoremap', []).filter(
  'ignoremap',
  () => (input) => {
    if (_.isEmpty(input)) return '------ Ignore Row ------';
    return input;
  }
);
