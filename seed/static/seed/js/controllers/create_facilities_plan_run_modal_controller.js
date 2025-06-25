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
    'columns',
    'existing_fpr',
    'level_name_index',
    'cycle_service',
    'inventory_service',
    'user_service',
    'ah_service',
    'facilities_plan_run_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      access_level_tree,
      facilities_plans,
      columns,
      existing_fpr,
      level_name_index,
      cycle_service,
      inventory_service,
      user_service,
      ah_service,
      facilities_plan_run_service
    ) {
      cycle_service.get_cycles_for_org($scope.org_id).then((cycles) => {
        $scope.cycles = cycles.cycles;
      });
      $scope.facilities_plans = facilities_plans;

      $scope.selected_columns = [];
      $scope.available_columns = () => columns.filter(({ id }) => !$scope.selected_columns.includes(id));

      $scope.select_column = () => {
        const selection = $scope.column_selection;
        $scope.column_selection = '';
        if (!$scope.selected_columns) {
          $scope.selected_columns = [];
        }
        $scope.selected_columns.push(selection);
      };

      $scope.click_remove_column = (id) => {
        $scope.selected_columns = $scope.selected_columns.filter((item) => item !== id);
      };

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

      if (existing_fpr){
        $scope.level_name_index = String(level_name_index)
        $scope.change_selected_level_index();
        $scope.access_level_instance_id = existing_fpr.ali
        $scope.run_name = existing_fpr.name
        $scope.facilities_plan = existing_fpr.facilities_plan
        $scope.baseline_cycle = existing_fpr.cycle
        $scope.selected_columns = existing_fpr.display_columns.map(c => c.id)

        console.log(existing_fpr.ali, $scope.access_level_instance_id)
        console.log(level_name_index, $scope.level_name_index)
        $scope.editing_existing_fpr = true;
      }

      $scope.get_column_display = (id) => {
        const record = _.find(columns, { id });
        if (record) {
          return record.displayName;
        }
      };

      $scope.save = () => {
        payload = {
          ali: $scope.access_level_instance_id,
          facilities_plan: $scope.facilities_plan,
          name: $scope.run_name,
          cycle: $scope.baseline_cycle,
          display_columns: $scope.selected_columns
        };

        if (existing_fpr){
          fn =  facilities_plan_run_service.update_facilities_plan_run(existing_fpr.id, payload)
        } else {
          fn =  facilities_plan_run_service.create_facilities_plan_run(payload)
        }
        fn.then((data) => {
          $state.reload();
          $uibModalInstance.dismiss();
        });
      };

      $scope.close = () => {
        $uibModalInstance.dismiss();
      };
    }
  ]);
