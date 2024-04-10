/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * FloatingPoint
 * Fix floating-point rounding errors
 *
 * @param {number} input - The input number
 * @param {number} [precision=15] - An integer specifying the number of significant digits (optional)
 *
 * @example 0.09999999999999998 | floatingPoint // 0.1
 */
angular.module('floatingPoint', []).filter(
  'floatingPoint',
  () => (input, precision = 15) => {
    if (_.isNil(input) || Number.isNaN(+input)) return input;

    return +parseFloat((+input).toPrecision(precision));
  }
);
