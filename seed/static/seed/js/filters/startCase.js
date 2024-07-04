/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * StartCase
 * For when you want to capitalize the first letter of each word
 * https://en.wikipedia.org/wiki/Letter_case#Stylistic_or_specialised_usage
 */
angular.module('startCase', []).filter(
  'startCase',
  () => (input) => {
    if (typeof input !== 'string') return input;

    return _.startCase(input.toLowerCase());
  }
);
