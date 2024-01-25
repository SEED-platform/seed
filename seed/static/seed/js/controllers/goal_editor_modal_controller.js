/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.goal_editor_modal', [])
    .controller('goal_editor_modal_controller', [
        '$scope',
        '$state',
        '$stateParams',
        '$uibModalInstance',
        'Notification',
        'goal_service',
        'auth_payload',
        'organization',
        'cycles',
        'area_columns',
        'eui_columns',
        'access_level_tree',
        'goal',
        function (
            $scope,
            $state,
            $stateParams,
            $uibModalInstance,
            Notification,
            goal_service,
            auth_payload,
            organization,
            cycles,
            area_columns,
            eui_columns,
            access_level_tree,
            goal,
        ) {
            $scope.auth = auth_payload.auth;
            $scope.organization = organization;
            $scope.goal = goal || {};
            $scope.access_level_tree = access_level_tree.access_level_tree;
            $scope.all_level_names = []
            access_level_tree.access_level_names.forEach((level, i) => $scope.all_level_names.push({index: i, name: level}))
            $scope.cycles = cycles;
            $scope.area_columns = area_columns;
            $scope.eui_columns = eui_columns;
            // allow "none" as an option
            if (!eui_columns.find(c => c.id === null && c.displayName === '')) {
                $scope.eui_columns.unshift({ id: null, displayName: '' });
            }
            $scope.valid = false;

            const get_goals = () => {
                goal_service.get_goals().then(result => {
                    $scope.goals = result.status == 'success' ? sort_goals(result.goals) : [];
                })
            }
            const sort_goals = (goals) => goals.sort((a, b) => a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1)
            get_goals()

            $scope.$watch('goal', (cur, old) => {
                $scope.goal_changed = cur != old;
            }, true)

            // ACCESS LEVEL INSTANCES
            // Users do not have permissions to create goals on levels above their own in the tree
            const remove_restricted_level_names = (user_ali) => {
                const path_keys = Object.keys(user_ali.data.path)
                $scope.level_names = []
                const reversed_names = $scope.all_level_names.slice().reverse()
                for (let index in reversed_names) {
                    $scope.level_names.push(reversed_names[index])
                    if (path_keys.includes(reversed_names[index].name)) {
                        break
                    }
                }
                $scope.level_names.reverse()
            }

            /* Build out access_level_instances_by_depth recurrsively */
            let access_level_instances_by_depth = {};
            const calculate_access_level_instances_by_depth = (tree, depth = 1) => {
                if (tree == undefined) return;
                if (access_level_instances_by_depth[depth] == undefined) access_level_instances_by_depth[depth] = [];
                tree.forEach(ali => {
                    if (ali.id == window.BE.access_level_instance_id) remove_restricted_level_names(ali)
                    access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name });
                    calculate_access_level_instances_by_depth(ali.children, depth + 1);
                })
            }
            calculate_access_level_instances_by_depth($scope.access_level_tree, 1);

            $scope.change_selected_level_index = () => {
                new_level_instance_depth = parseInt($scope.goal.level_name_index) + 1
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
            }
            $scope.change_selected_level_index()

            $scope.set_goal = (goal) => {
                $scope.goal = goal;
                $scope.change_selected_level_index();;
            }

            $scope.save_goal = () => {
                $scope.goal_changed = false;
                const goal_fn = $scope.goal.id ? goal_service.update_goal : goal_service.create_goal
                // if new goal, assign org id
                $scope.goal.organization = $scope.goal.organization || $scope.organization.id
                goal_fn($scope.goal).then(result => {
                    if (result.status === 200 || result.status === 201) {
                        Notification.success({ message: 'Goal saved', delay: 5000 });
                        $scope.errors = null;
                        $scope.goal.id = $scope.goal.id || result.data.id;
                        get_goals()
                        $scope.set_goal($scope.goal)
                    } else {
                        $scope.errors = [`Unexpected response status: ${result.status}`];
                        let result_errors = 'errors' in result.data ? result.data.errors : result.data
                        if (result_errors instanceof Object) {
                            for (let key in result_errors) {
                                let key_string = key == 'non_field_errors' ? 'Error' : key;
                                $scope.errors.push(`${key_string}: ${JSON.stringify(result_errors[key])}`)
                            }
                        } else {
                            $scope.errors = $scope.errors.push(result_errors)
                        }
                    };
                });
            }

            $scope.delete_goal = (goal_id) => {
                const goal = $scope.goals.find(goal => goal.id === goal_id)
                if (!goal) return Notification.warning({ message: 'Unexpected Error', delay: 5000 })

                if (!confirm(`Are you sure you want to delete Goal "${goal.name}"`)) return

                goal_service.delete_goal(goal_id).then((response) => {
                    if (response.status === 204) {
                        Notification.success({ message: 'Goal deleted successfully', delay: 5000 });
                    } else {
                        Notification.warning({ message: 'Unexpected Error', delay: 5000 })
                    }
                    get_goals()
                    if (goal_id == $scope.goal.id) {
                        $scope.goal = null;
                    }
                })
            }

            $scope.new_goal = () => {
                $scope.goal = {};
            }

            $scope.close = () => {
                let goal_name = $scope.goal ? $scope.goal.name : null;
                $uibModalInstance.close(goal_name)
            }
        }
    ]
)
