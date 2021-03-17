/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * filter 'fromNow' using the moment.js function 'fromNow()'
 * see: http://momentjs.com/
 */
angular.module('fromNow', []).filter('fromNow', function () {
  return function (dateString) {
    if (_.isNumber(dateString) || /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z/.test(dateString)) {
      var m = moment(dateString);
      if (m.isValid()) return m.fromNow();
    }
    return 'a few seconds ago';
  };
});
