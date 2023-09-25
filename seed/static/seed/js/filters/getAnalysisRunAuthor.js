/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('getAnalysisRunAuthor', []).filter('getAnalysisRunAuthor', function () {
  return function (users) {
    if (!users || users.length < 1) {
      return ''; // no user, display nothing
    }
    const user = users[0];
    if (!user.first_name || !user.last_name) {
      return user.email; // no full name, display email
    }
    return [user.last_name, user.first_name].join(', '); // display full name
  };
});
