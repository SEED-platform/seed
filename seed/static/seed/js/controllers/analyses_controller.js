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
    function (
      $scope,
      analyses_payload,
      organization_payload,
      users_payload,
      auth_payload,
      urls,
      analyses_service,
      Notification,
    ) {
      $scope.org = organization_payload;
      $scope.auth = auth_payload.auth;
      $scope.analyses = analyses_payload.analyses;
      $scope.users = users_payload.users;

      // Stores functions for stopping the polling of analysis progress. Keyed by analysis id
      const analysis_polling_stoppers = {}

      $scope.$on('$destroy', () => {
        // cancel all polling
        Object.values(analysis_polling_stoppers).forEach(stop_func => stop_func())
      })

      const refresh_analyses = function () {
        analyses_service.get_analyses_for_org($scope.org.id)
          .then(function (data) {
            $scope.analyses = data.analyses;
          });
      };

      const refresh_analysis = (analysis_id) => {
        // update analysis in scope
        return analyses_service.get_analysis_for_org(analysis_id, $scope.org.id)
          .then(data => {
            const analysis_index = $scope.analyses.findIndex(analysis => {
              return analysis.id === analysis_id
            })
            $scope.analyses[analysis_index] = data.analysis
            return data.analysis
          })
      }

      // add flag to the analysis indicating it has no currently running tasks
      // Used to determine if we should indicate on UI if an analysis's status is being polled
      const mark_analysis_not_active = (analysis_id) => {
        const analysis_index = $scope.analyses.findIndex(analysis => {
          return analysis.id === analysis_id
        })
        $scope.analyses[analysis_index]._finished_with_tasks = true
      }

      // Entry point for keeping track of analysis progress
      // Refreshes analysis in $scope when necessary
      const poll_analysis_progress = (analysis) => {
        if (analysis_polling_stoppers[analysis.id]) {
          analysis_polling_stoppers[analysis.id]()
        }

        const stop_func = analyses_service.check_progress_loop(analysis, refresh_analysis, mark_analysis_not_active)        
        analysis_polling_stoppers[analysis.id] = stop_func
      }

      // start polling all of the analyses
      $scope.analyses.forEach(analysis => {
        poll_analysis_progress(analysis)
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
              refresh_analysis(analysis_id)
                .then((updated_analysis) => {
                  poll_analysis_progress(updated_analysis)
                })
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
              refresh_analysis(analysis_id)
                .then((updated_analysis) => {
                  poll_analysis_progress(updated_analysis)
                })
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
              // stop polling and remove the analysis from the scope
              analysis_polling_stoppers[analysis_id]()
              const analysis_index = $scope.analyses.findIndex(analysis => {
                return analysis.id === analysis_id
              })
              $scope.analyses.splice(analysis_index, 1)
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
