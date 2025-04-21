/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.facilities_plan', [])
  .controller('facilities_plan_controller', [
    '$scope',
    'facilities_plans',
    'facilities_plan_runs',
    'facilities_plan_run_service',
    function (
      $scope,
      facilities_plans,
      facilities_plan_runs,
      facilities_plan_run_service,
    ) {
      $scope.facilities_plan_runs = facilities_plan_runs.data;
      $scope.current_facilities_plan_run_id = null;
      $scope.current_facilities_plan_run = null;

      $scope.change_facilities_pan = () => {
        $scope.current_facilities_plan_run = $scope.facilities_plan_runs.find(fp => fp.id == $scope.current_facilities_plan_run_id);
        facilities_plan_run_service.get_facilities_plan_run_properties($scope.current_facilities_plan_run_id).then(data => {
          console.log(data)
        });
      }


    }]);
