/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.facilities_plan', [])
  .controller('facilities_plan_controller', [
    '$scope',
    'facilities_plans',
    function (
      $scope,
      facilities_plans,
    ) {
      $scope.facilities_plans = facilities_plans.data;
      $scope.current_facilities_plan_id = null;
      $scope.current_facilities_plan = null;

      $scope.change_facilities_pan = () => {
        $scope.current_facilities_plan = $scope.facilities_plans.find(fp => fp.id == $scope.current_facilities_plan_id);
        console.log($scope.current_facilities_plan)
      }
    }]);
