/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
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
