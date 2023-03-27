/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * TolerantNumber
 * Convert to number with comma separators and fixed decimals if possible, otherwise return input
 */
angular.module('tolerantNumber', []).filter('tolerantNumber', () => (input, fixed_digits) => {
  if (_.isNil(input)) return input;

  const num = Number(input.toString().replace(/,/g, '').trim());
  if (Number.isNaN(num)) return input;

  // TODO: consider making the locale dynamic for i18n
  return num.toLocaleString('en-US', {
    minimumFractionDigits: fixed_digits,
    maximumFractionDigits: fixed_digits
  });
});
