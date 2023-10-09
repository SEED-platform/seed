/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * filter 'fromNow' using the moment.js function 'fromNow()'
 * see: http://momentjs.com/
 */
angular.module('fromNow', []).filter(
  'fromNow',
  // eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
  function () {
    return (dateString) => {
      if (_.isNumber(dateString) || /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z/.test(dateString)) {
        const m = moment(dateString);
        if (m.isValid()) return m.fromNow();
      }
      return 'a few seconds ago';
    };
  }
);
