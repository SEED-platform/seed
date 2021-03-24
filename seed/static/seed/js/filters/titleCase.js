/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
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
