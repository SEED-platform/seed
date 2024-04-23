/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.goal_editor_modal', [])
  .controller('goal_editor_modal_controller', [
    '$scope',
    '$state',
    '$stateParams',
    '$uibModalInstance',
    'Notification',
    'ah_service',
    'goal_service',
    'access_level_tree',
    'area_columns',
    'auth_payload',
    'cycles',
    'eui_columns',
    'goal',
    'organization',
    'write_permission',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      $uibModalInstance,
      Notification,
      ah_service,
      goal_service,
      access_level_tree,
      area_columns,
      auth_payload,
      cycles,
      eui_columns,
      goal,
      organization,
      write_permission
    ) {
      $scope.auth = auth_payload.auth;
      $scope.organization = organization;
      $scope.write_permission = write_permission;
      $scope.goal = goal || {};
      $scope.access_level_tree = access_level_tree.access_level_tree;
      $scope.level_names = access_level_tree.access_level_names.map((level, i) => ({
        index: i,
        name: level
      }));
      $scope.cycles = cycles;
      $scope.area_columns = area_columns;
      $scope.eui_columns = eui_columns;
      // allow "none" as an option
      if (!eui_columns.find((col) => col.id === null && col.displayName === '')) {
        $scope.eui_columns.unshift({ id: null, displayName: '' });
      }
      $scope.valid = false;

      const sort_goals = (goals) => goals.sort((a, b) => (a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1));
      const get_goals = () => {
        goal_service.get_goals().then((result) => {
          $scope.goals = result.status === 'success' ? sort_goals(result.goals) : [];
        });
      };
      get_goals();

      $scope.$watch('goal', (cur, old) => {
        $scope.goal_changed = cur !== old;
      }, true);

      const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);

      $scope.change_selected_level_index = () => {
        const new_level_instance_depth = parseInt($scope.goal.level_name_index, 10) + 1;
        $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
      };
      $scope.change_selected_level_index();

      $scope.set_goal = (goal) => {
        $scope.goal = goal;
        $scope.change_selected_level_index();
      };

      $scope.save_goal = () => {
        $scope.goal_changed = false;
        const goal_fn = $scope.goal.id ? goal_service.update_goal : goal_service.create_goal;
        // if new goal, assign org id
        $scope.goal.organization = $scope.goal.organization || $scope.organization.id;
        goal_fn($scope.goal).then((result) => {
          if (result.status === 200 || result.status === 201) {
            Notification.success({ message: 'Goal saved', delay: 5000 });
            $scope.errors = null;
            $scope.goal.id = $scope.goal.id || result.data.id;
            get_goals();
            $scope.set_goal($scope.goal);
          } else {
            $scope.errors = [`Unexpected response status: ${result.status}`];
            const result_errors = 'errors' in result.data ? result.data.errors : result.data;
            if (result_errors instanceof Object) {
              for (const key in result_errors) {
                const key_string = key === 'non_field_errors' ? 'Error' : key;
                $scope.errors.push(`${key_string}: ${JSON.stringify(result_errors[key])}`);
              }
            } else {
              $scope.errors = $scope.errors.push(result_errors);
            }
          }
        });
      };

      $scope.delete_goal = (goal_id) => {
        const goal = $scope.goals.find((goal) => goal.id === goal_id);
        if (!goal) return Notification.warning({ message: 'Unexpected Error', delay: 5000 });

        if (!confirm(`Are you sure you want to delete Goal "${goal.name}"`)) return;

        goal_service.delete_goal(goal_id).then((response) => {
          if (response.status === 204) {
            Notification.success({ message: 'Goal deleted successfully', delay: 5000 });
          } else {
            Notification.warning({ message: 'Unexpected Error', delay: 5000 });
          }
          get_goals();
          if (goal_id === $scope.goal.id) {
            $scope.goal = null;
          }
        });
      };

      $scope.new_goal = () => {
        $scope.goal = {};
      };

      $scope.close = () => {
        const goal_name = $scope.goal ? $scope.goal.name : null;
        $uibModalInstance.close(goal_name);
      };
    }]);
