/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
      $scope.is_object = _.isObject;

      let stop_func = () => {};
      const starting_analysis_status = $scope.analysis.status;

      $scope.allowActions = true

      $scope.$on('$destroy', () => {
        stop_func();
      });

      const refresh_analysis = (analysis_id) => {
        // update analysis in scope
        return analyses_service.get_analysis_for_org(analysis_id, $scope.org.id)
          .then(data => {
            $scope.analysis = data.analysis;
            return data.analysis;
          });
      };

      // add flag to the analysis indicating it has no currently running tasks
      // Used to determine if we should indicate on UI if an analysis's status is being polled
      const mark_analysis_not_active = (/*analysis_id*/) => {
        $scope.analysis._finished_with_tasks = true;

        // if the status of the analysis has changed since we first loaded the page, refresh everything
        // so that analysis results and messages are updated. (this is lazy, but is good enough for now)
        if (starting_analysis_status != $scope.analysis.status) {
          $state.reload();
        }
      };

      stop_func = analyses_service.check_progress_loop($scope.analysis, refresh_analysis, mark_analysis_not_active);
    }]);
