/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * TitleCase
 * For when you want to capitalize each word, remove underscores.
 */
angular.module('titleCase', []).filter('titleCase', function () {

  return function (input) {
    if (_.isNil(input)) {
      return input;
    }
    input = input.toString();
    input = input.replace(/_/g, ' ');
    input = input.replace(/(?:^|\s)\S/g, function (a) {
      return a.toUpperCase();
    });

    return input;
  };

});
