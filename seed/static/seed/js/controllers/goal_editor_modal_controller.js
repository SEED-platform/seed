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
        'goal_service',
        'organization',
        'cycles',
        'goal_columns',
        'access_level_tree',
        'goal',
        function (
            $scope,
            $state,
            $stateParams,
            $uibModalInstance,
            goal_service,
            organization,
            cycles,
            goal_columns,
            access_level_tree,
            goal,
        ) {
            $scope.organization = organization;
            // form data
            $scope.goal = goal;
            // existing goal
            $scope.selected_goal = goal.id ? goal : null;
            $scope.access_level_tree = access_level_tree.access_level_tree;
            $scope.level_names = []
            access_level_tree.access_level_names.forEach((level, i) => $scope.level_names.push({index: i, name: level}))
            $scope.cycles = cycles;
            $scope.goal_columns = goal_columns;
            $scope.valid = false;

            const get_goals = () => {
                goal_service.get_goals().then(result => {
                    $scope.goals = result.status == 'success' ? result.goals : []
                })
            }
            get_goals()

            // allow "none" as an option
            $scope.goal_columns.unshift({ id: null, displayName: "" });
            // Prevent user from hitting save changes multiple times
            $scope.$watch('goal', (cur, old) => {
                $scope.goal_changed = cur != old;
            }, true)

            // ACCESS LEVEL INSTANCES
            /* Build out access_level_instances_by_depth recurrsively */
            let access_level_instances_by_depth = {};
            const calculate_access_level_instances_by_depth = (tree, depth = 1) => {
                if (tree == undefined) return;
                if (access_level_instances_by_depth[depth] == undefined) access_level_instances_by_depth[depth] = [];
                tree.forEach(ali => {
                    access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name });
                    calculate_access_level_instances_by_depth(ali.children, depth + 1);
                })
            }
            calculate_access_level_instances_by_depth($scope.access_level_tree, 1);

            $scope.change_selected_level_index = () => {
                new_level_instance_depth = parseInt($scope.goal.level_name_index) + 1
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
                console.log($scope.potential_level_instances);
            }
            $scope.change_selected_level_index()

            $scope.set_selected_goal = (goal) => {
                $scope.selected_goal = goal
                $scope.goal = goal
                $scope.change_selected_level_index()
            }

            $scope.save_goal = () => {
                $scope.goal_changed = false;
                const goal_fn = $scope.goal.id ? goal_service.update_goal : goal_service.create_goal
                // if new goal, assign org id
                $scope.goal.organization = $scope.goal.organization || $scope.organization.id
                goal_fn($scope.goal).then(result => {
                    console.log('res', result)
                    if (result.status == 200 || result.status == 201) {
                        $scope.errors = null;
                        $scope.goal.id = $scope.goal.id || result.data.id
                        get_goals()
                        $scope.set_selected_goal($scope.goal)
                    } else {
                        $scope.errors = [`Unexpected response status: ${result.status}`];
                        for (let key in result.data) {
                            if (typeof result.data[key] == 'object') {
                                const key_data = result.data[key]
                                for (let k in key_data) {
                                    $scope.errors.push(`${k}: ${key_data[k]}`)
                                }
                            } else {
                                $scope.errors.push(`${key}: ${result.data[key]}`)
                            }
                        }
                    };
                });
            }

            $scope.delete_goal = (goal_id) => {
                goal_service.delete_goal(goal_id).then(() =>{
                    get_goals()
                    if (goal_id == $scope.selected_goal.id) {
                        $scope.selected_goal = null;
                        $scope.goal = null;
                    }
                })
            }

            $scope.new_goal = () => {
                $scope.selected_goal = null;
                $scope.goal = {}
            }

            $scope.close = () => {
                let goal_name = $scope.goal ? $scope.goal.name : null
                $uibModalInstance.close(goal_name)
            }
        }
    ]
)
