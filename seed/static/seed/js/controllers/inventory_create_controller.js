/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.inventory_create', []).controller('inventory_create_controller', [
    '$scope',
    '$window',
    '$stateParams',
    'ah_service',
    'inventory_service',
    'access_level_tree',
    'all_columns',
    'cycles',
    'profiles',
    'organization_payload',
    // eslint-disable-next-line func-names
    function (
        $scope,
        $window,
        $stateParams,
        ah_service,
        inventory_service,
        access_level_tree,
        all_columns,
        cycles,
        profiles,
        organization_payload,
    ) {
        $scope.inventory = {};
        $scope.inventory_type = $stateParams.inventory_type;
        $scope.inventory_types = ['Property', 'TaxLot'];
        const table_name = $scope.inventory_type === 'taxlots' ? 'TaxLotState' : 'PropertyState';
        $scope.cycles = cycles.cycles;
        $scope.profiles = profiles;
        $scope.profile = [];
        $scope.columns = all_columns;

        $scope.matching_columns = [];
        $scope.extra_columns = [];
        $scope.canonical_columns = [];
        $scope.columns.forEach((c) => {
            if (c.table_name == table_name) {
                if (c.is_matching_criteria) $scope.matching_columns.push(c);
                if (c.is_extra_data) $scope.extra_columns.push(c);
                if (!c.is_extra_data && !c.derived_column) $scope.canonical_columns.push(c);
            }
        });
        $scope.inventory.form_columns =[...$scope.matching_columns];
        $scope.form_values = [];

        $scope.remove_column = (index) => {
            $scope.inventory.form_columns.splice(index, 1)
            $scope.form_values[index] = null;
        };
        $scope.add_column = () => $scope.inventory.form_columns.push({displayName: '', table_name: table_name});


        // ACCESS LEVEL TREE
        $scope.access_level_tree = access_level_tree.access_level_tree;
        $scope.level_names = access_level_tree.access_level_names.map((level, i) => ({
            index: i,
            name: level
        }));
        const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);
        $scope.change_selected_level_index = () => {
            const new_level_instance_depth = parseInt($scope.inventory.level_name_index, 10) + 1;
            $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
        };
        $scope.inventory.level_name_index = $scope.level_names.at(-1).index;
        $scope.change_selected_level_index();
        $scope.inventory.access_level_instance = $scope.potential_level_instances.at(0).id;

        // COLUMN LIST PROFILES 
        $scope.set_columns = (type) => {
            remove_empty_last_column();
            switch (type) {
                case 'canonical':
                    $scope.inventory.form_columns = Array.from(new Set([...$scope.inventory.form_columns, ...$scope.canonical_columns]));
                    break;
                case 'extra':
                    $scope.inventory.form_columns = Array.from(new Set([...$scope.inventory.form_columns, ...$scope.extra_columns]));
                    break;
                default:
                    $scope.inventory.form_columns = [...$scope.matching_columns];
                    $scope.inventory.form_columns = $scope.inventory.form_columns.map(c => ({...c, value: null}));
                    $scope.form_values = [];
            }
        }

        const remove_empty_last_column = () => {
            if (!_.isEmpty($scope.inventory.form_columns) && $scope.inventory.form_columns.at(-1).displayName === '') {
                $scope.inventory.form_columns.pop();
            }
        }


        // FORM LOGIC
        $scope.change_profile = () => {
            const profile_column_names = $scope.profile.columns.map(p => p.column_name);
            $scope.inventory.form_columns = $scope.columns.filter(c => profile_column_names.includes(c.column_name))
        }

        $scope.select_column = (column, idx) => {
            column.value = $scope.form_values.at(idx);
            $scope.inventory.form_columns[idx] = column;
        }

        $scope.change_column = (displayName, idx) => {
            const defaults = {
                table_name: table_name,
                is_extra_data: true,
                is_matching_criteria: false,
                data_type: 'string',
            }
            let column = $scope.columns.find(c => c.displayName === displayName) || {displayName: displayName};
            column = {...defaults, ...column};

            column.value = $scope.form_values.at(idx);
            $scope.inventory.form_columns[idx] = column;
        };

        $scope.change_value = (value, idx) => {
            $scope.form_values[idx] = value;
        }

        $scope.save_inventory = () => {
            console.log('save_inventory', $scope.inventory)
        }
        







    }
]);
