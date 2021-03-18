/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
