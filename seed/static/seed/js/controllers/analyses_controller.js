/*
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.analyses', [])
  .controller('analyses_controller', [
    '$scope',
    'analyses_payload',
    'organization_payload',
    'users_payload',
    'auth_payload',
    'urls',
    function (
      $scope,
      analyses_payload,
      organization_payload,
      users_payload,
      auth_payload,
      urls
    ) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
      $scope.analyses = analyses_payload.analyses;
      $scope.users = users_payload.users;
    }
  ])
  .filter('get_run_duration', function() {

    return function(analysis) {
      if (!analysis['start_time'] || !analysis['end_time']) {
        return ''; // no start and/or stop time, display nothing
      }

      let oneSecond = 1000;
      var oneMinute = oneSecond * 60;
      var oneHour = oneMinute * 60;
      var oneDay = oneHour * 24;

      let millseconds = (new Date(analysis['end_time'])).getTime() - (new Date(analysis['start_time'])).getTime();
      let seconds = Math.floor((millseconds % oneMinute) / oneSecond);
      let minutes = Math.floor((millseconds % oneHour) / oneMinute);
      let hours = Math.floor((millseconds % oneDay) / oneHour);
      let days = Math.floor(millseconds / oneDay);

      let time = [];
      if (days !== 0) time.push((days !== 1) ? (days + ' days') : (days + ' day'));
      if (hours !== 0) time.push((hours !== 1) ? (hours + ' hours') : (hours + ' hour'));
      if (minutes !== 0) time.push((minutes !== 1) ? (minutes + ' minutes') : (minutes + ' minute'));
      if (seconds !== 0 || millseconds < 1000) time.push((seconds !== 1) ? (seconds + ' seconds') : (seconds + ' second'));
      return time.join(', ');
    };
  })
  .filter('get_run_author', function() {

    return function(users) {
      if (users.length < 1) {
        return ''; // no user, display nothing
      }
      user = users[0];
      if (!user['first_name'] || !user['last_name']) {
        return user['email']; // no full name, display email
      }
      return [user['last_name'], user['first_name']].join(', '); // display full name
    };
  });
