/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * TitleCase
 * For when you want to capitalize each word, remove underscores.
 */
angular.module('titleCase', []).filter(
  'titleCase',
  // eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
  function () {
    return (input) => {
      if (_.isNil(input)) {
        return input;
      }
      input = input.toString();
      input = input.replace(/_/g, ' ');
      input = input.replace(/(?:^|\s)\S/g, (a) => a.toUpperCase());

      return input;
    };
  }
);
