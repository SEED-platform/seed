/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * filter 'fromNow' using the moment.js function 'fromNow()'
 * see: http://momentjs.com/
 */
angular.module('fromNow', []).filter(
  'fromNow',
  () => (dateString) => {
    if (_.isNumber(dateString) || /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z/.test(dateString)) {
      const m = moment(dateString);
      if (m.isValid()) return m.fromNow();
    }
    return 'a few seconds ago';
  }
);
