/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.create_facilities_plan_run_modal', [])
  .controller('create_facilities_plan_run_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'access_level_tree',
    'facilities_plans',
    'cycle_service',
    'inventory_service',
    'user_service',
    'ah_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      access_level_tree,
      facilities_plans,
      cycle_service,
      inventory_service,
      user_service,
      ah_service,
    ) {
      cycle_service.get_cycles_for_org($scope.org_id).then((cycles) => {
        $scope.cycles = cycles.cycles;
      });
      $scope.facilities_plans = facilities_plans;

      $scope.users_access_level_instance_id = user_service.get_access_level_instance().id;
      $scope.access_level_instance_id = parseInt($scope.users_access_level_instance_id, 10);
      $scope.facilities_plan = null;
      $scope.run_name = null;
      $scope.baseline_cycle = null;

      const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth(access_level_tree.access_level_tree);
      const [users_depth] = Object.entries(access_level_instances_by_depth).find(([, x]) => x.length === 1 && x[0].id === parseInt($scope.users_access_level_instance_id, 10));
      $scope.level_name_index = users_depth;
      $scope.level_names = access_level_tree.access_level_names.slice(users_depth - 1);

      $scope.change_selected_level_index = () => {
        const new_level_instance_depth = parseInt($scope.level_name_index, 10) + parseInt(users_depth, 10);
        $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
        // for (const key in $scope.potential_level_instances) {
        //   $scope.potential_level_instances[key].name = path_to_string($scope.potential_level_instances[key].path);
        // }
        $scope.access_level_instance_id = null;
      };



      $scope.save = () => {
        console.log("$scope.access_level_instance_id", $scope.access_level_instance_id)
        console.log("$scope.facilities_plan", $scope.facilities_plan)
        console.log("$scope.run_name", $scope.run_name)
        console.log("$scope.baseline_cycle", $scope.baseline_cycle)
      };

      $scope.close = () => {
        $uibModalInstance.dismiss();
      };
    }
  ]);
