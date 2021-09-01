/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
    'analyses_service',
    'Notification',
    'uploader_service',
    function (
      $scope,
      analyses_payload,
      organization_payload,
      users_payload,
      auth_payload,
      urls,
      analyses_service,
      Notification,
      uploader_service
    ) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
      $scope.analyses = analyses_payload.analyses;
      $scope.users = users_payload.users;

      const refresh_analyses = function () {
        analyses_service.get_analyses_for_org($scope.org.id)
          .then(function (data) {
            $scope.analyses = data.analyses;
          });
      };

      // Check the progress of the analysis. Every time a task completes, refresh
      // the analysis for the $scope and see if there's another trackable task to check
      const check_analysis_progress_loop = (analysis_id) => {
        analyses_service.get_progress_key(analysis_id)
          .then(data => {
            if (!data.progress_key) {
              // analysis isn't in a trackable state/status, stop checking
              return
            }

            const analysis_index = $scope.analyses.findIndex(analysis => {
              return analysis.id === analysis_id
            })
            $scope.analyses[analysis_index]._tracking_progress = true

            uploader_service.check_progress_loop(data.progress_key, 0, 1, () => {
              analyses_service.get_analysis_for_org(analysis_id, $scope.org.id)
                .then(data => {
                  const analysis_index = $scope.analyses.findIndex(analysis => {
                    return analysis.id === analysis_id
                  })
                  $scope.analyses[analysis_index] = data.analysis

                  // start tracking the progress again
                  check_analysis_progress_loop(analysis_id)
                })
            }, () => {},
            {})
          })
      }

      $scope.analyses.forEach(analysis => {
        check_analysis_progress_loop(analysis.id)
      })

      $scope.start_analysis = function (analysis_id) {
        const analysis = $scope.analyses.find(function (a) {
          return a.id === analysis_id;
        });
        analysis.status = 'Starting...';

        analyses_service.start_analysis(analysis_id)
          .then(function (result) {
            if (result.status === 'success') {
              Notification.primary('Analysis started');
              refresh_analyses();
              uploader_service.check_progress_loop(result.progress_key, 0, 1, function () {
                refresh_analyses();
              }, function () {
                refresh_analyses();
              }, {});
            } else {
              Notification.error('Failed to start analysis: ' + result.message);
            }
          });
      };

      $scope.stop_analysis = function (analysis_id) {
        const analysis = $scope.analyses.find(function (a) {
          return a.id === analysis_id;
        });
        analysis.status = 'Stopping...';

        analyses_service.stop_analysis(analysis_id)
          .then(function (result) {
            if (result.status === 'success') {
              Notification.primary('Analysis stopped');
              refresh_analyses();
            } else {
              Notification.error('Failed to stop analysis: ' + result.message);
            }
          });
      };

      $scope.delete_analysis = function (analysis_id) {
        const analysis = $scope.analyses.find(function (a) {
          return a.id === analysis_id;
        });
        analysis.status = 'Deleting...';

        analyses_service.delete_analysis(analysis_id)
          .then(function (result) {
            if (result.status === 'success') {
              Notification.primary('Analysis deleted');
              refresh_analyses();
            } else {
              Notification.error('Failed to delete analysis: ' + result.message);
            }
          });
      };
      $scope.has_children = function (value) {
        if (typeof value == 'object') {
          return true;
        }
      };

    }
  ])
  .filter('get_run_duration', function () {

    return function (analysis) {
      if (!analysis || !analysis.start_time || !analysis.end_time) {
        return ''; // no start and/or stop time, display nothing
      }

      let oneSecond = 1000;
      var oneMinute = oneSecond * 60;
      var oneHour = oneMinute * 60;
      var oneDay = oneHour * 24;

      let milliseconds = (new Date(analysis.end_time)).getTime() - (new Date(analysis.start_time)).getTime();
      let seconds = Math.floor((milliseconds % oneMinute) / oneSecond);
      let minutes = Math.floor((milliseconds % oneHour) / oneMinute);
      let hours = Math.floor((milliseconds % oneDay) / oneHour);
      let days = Math.floor(milliseconds / oneDay);

      let time = [];
      if (days !== 0) time.push((days !== 1) ? (days + ' days') : (days + ' day'));
      if (hours !== 0) time.push((hours !== 1) ? (hours + ' hours') : (hours + ' hour'));
      if (minutes !== 0) time.push((minutes !== 1) ? (minutes + ' minutes') : (minutes + ' minute'));
      if (seconds !== 0 || milliseconds < 1000) time.push((seconds !== 1) ? (seconds + ' seconds') : (seconds + ' second'));
      return time.join(', ');
    };
  });
