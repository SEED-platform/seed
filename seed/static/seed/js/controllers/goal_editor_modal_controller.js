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
        'level_names',
        'access_level_tree',
        function (
            $scope,
            $state,
            $stateParams,
            $uibModalInstance,
            goal_service,
            organization,
            cycles,
            goal_columns,
            level_names,
            access_level_tree,
        ) {
            $scope.access_level_tree = access_level_tree;
            $scope.cycles = cycles;
            $scope.goal_columns = goal_columns;
            const blank_column = { id: null, displayName: "" };
            $scope.goal_columns.unshift(blank_column);
            $scope.level_names = level_names ;
            $scope.organization = organization;
            $scope.valid = false;

            $scope.goal = { organization: $scope.organization.id };

            // how do we prevent users from hitting create button over and over?
            $scope.$watch('goal', (cur, old) => {
                $scope.goal_changed = cur != old;
            }, true)

            // ACCESS LEVEL INSTANCES
            /* Build out access_level_instances_by_depth recurrsively */
            let access_level_instances_by_depth = {};
            const calculate_access_level_instances_by_depth = function (tree, depth = 1) {
                if (tree == undefined) return;
                if (access_level_instances_by_depth[depth] == undefined) access_level_instances_by_depth[depth] = [];
                tree.forEach(ali => {
                    access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name });
                    calculate_access_level_instances_by_depth(ali.children, depth + 1);
                })
            }
            calculate_access_level_instances_by_depth($scope.access_level_tree, 1);

            $scope.change_selected_level_index = function () {
                new_level_instance_depth = parseInt($scope.goal.level_name_index) + 1
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
                console.log($scope.potential_level_instances);
            }


            $scope.save_goal = () => {
                $scope.goal_changed = false;
                const goal_fn = $scope.goal.id ? goal_service.update_goal : goal_service.create_goal
                goal_fn($scope.goal).then(result => {
                    console.log('res', result)
                    if (result.status == 200 || result.status == 201) {
                        $scope.errors = null;
                    } else {
                        $scope.errors = [`Unexpected response status: ${result.status}`];
                        for (let key in result.data) {
                            $scope.errors.push(`${key}: ${result.data[key]}`)
                        }
                    };
                });
            }

            $scope.close = () => {
                $uibModalInstance.dismiss();
            }
        }
    ]
)
    