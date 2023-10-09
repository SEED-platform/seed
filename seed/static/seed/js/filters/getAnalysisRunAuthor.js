/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('getAnalysisRunAuthor', []).filter(
  'getAnalysisRunAuthor',
  // eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
  function () {
    return (users) => {
      if (!users || users.length < 1) {
        return ''; // no user, display nothing
      }
      const user = users[0];
      if (!user.first_name || !user.last_name) {
        return user.email; // no full name, display email
      }
      return [user.last_name, user.first_name].join(', '); // display full name
    };
  }
);
