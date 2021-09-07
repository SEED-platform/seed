/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.analysis_details', [])
  .controller('analysis_details_controller', [
    '$scope',
    '$state',
    'analyses_service',
    function (
      $scope,
      $state,
      analyses_service
    ) {
      let stop_func = () => {}
      const starting_analysis_status = $scope.analysis.status

      $scope.$on('$destroy', () => {
        stop_func()
      })

      const refresh_analysis = (analysis_id) => {
        // update analysis in scope
        return analyses_service.get_analysis_for_org(analysis_id, $scope.org.id)
          .then(data => {
            $scope.analysis = data.analysis
            return data.analysis
          })
      }

      // add flag to the analysis indicating it has no currently running tasks
      // Used to determine if we should indicate on UI if an analysis's status is being polled
      const mark_analysis_not_active = (analysis_id) => {
        $scope.analysis._finished_with_tasks = true

        // if the status of the analysis has changed since we first loaded the page, refresh everything
        // so that analysis results and messages are updated. (this is lazy, but is good enough for now)
        if (starting_analysis_status != $scope.analysis.status) {
          $state.reload()
        }
      }

      stop_func = analyses_service.check_progress_loop($scope.analysis, refresh_analysis, mark_analysis_not_active)
    }]);
