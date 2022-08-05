/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_aggregation_editor', []).controller('data_aggregation_editor_controller', [
    '$scope',
    '$stateParams',
    '$state',
    'all_columns',
    'data_aggregation_service',
    'modified_service',
    'organization_payload',
    'spinner_utility',
    'Notification',

    function (
        $scope,
        $stateParams,
        $state,
        all_columns,
        data_aggregation_service,
        modified_service,
        organization_payload,
        spinner_utility,
        Notification,

        ) {
        modified_service.setModified();
        $scope.inventory_type = $stateParams.inventory_type;
        $scope.data_aggregation_id = $stateParams.data_aggregation_id;
        $scope.all_columns = all_columns;
        $scope.organization = organization_payload.organization;
        $scope.data_aggregation_type_options = ['Average', 'Count', 'Max', 'Min', 'Sum'];

        $scope.validate_data_aggregation = () => {
            no_empty_values = Object.values($scope.data_aggregation).every(Boolean);
            return no_empty_values || validate_name();
        };


        const validate_name = () => {
            const agg_with_same_name = $scope.data_aggregations ? $scope.data_aggregations.find(da => da.name == $scope.data_aggregation.name) : null;
            $scope.name_error_message = (agg_with_same_name && !$scope.data_aggregation_id)  ? 'A Data Aggregation with that name already exists' : null;
            return ($scope.name_error_message) ? false : true;
        };


        $scope.capitalize = (str) => {
            return str[0].toUpperCase() + str.slice(1);
        };


        $scope.create_data_aggregation = () => {
            let { name, type, column } = $scope.data_aggregation;
            return data_aggregation_service.create_data_aggregation($scope.organization.id, { name, type, column });
        };


        $scope.create_or_update_data_aggregation = () => {
            let api_call = null;
            const creating = !$scope.data_aggregation.id;

            spinner_utility.show();
            if (creating) {
                api_call = () => $scope.create_data_aggregation();
            } else {
                api_call = () => $scope.update_data_aggregation();
            };

            api_call()
                .then(res => {
                    spinner_utility.hide();
                    modified_service.resetModified();
                    if (res.status == 'Error') {
                        Notification.error(res.message)
                    } else {
                        Notification.success(`${creating ? 'Created' : 'Updated'} "${res.data_aggregation.name}"`);
                        $state.go('data_aggregations', { inventory_type: 'properties' });
                    }
                }).catch(err => {
                    spinner_utility.hide();
                    $log.error(err);
                    console.log('ERROR HERE')
                    if (err.data && err.data.errors) {
                        $scope.errors_from_server = err.data.errors;
                    } else {
                        throw Error(`Something unexpectedly went wrong: ${err}`);
                    }
                });

        }

        $scope.update_data_aggregation = () => {
            let { name, type, column } = $scope.data_aggregation;
            return data_aggregation_service.update_data_aggregation($scope.organization.id, $scope.data_aggregation.id, { name, type, column });
        }


        const get_data_aggregations = () => {
            data_aggregation_service.get_data_aggregations($scope.organization.id)
                .then(response => {
                    response.message.forEach(da => {
                        column = all_columns.find(c => c.id == da.column)
                        da.column_id_name = column.displayName
                        da.column_name = column.displayName
                    })
                    $scope.data_aggregations = response.message
                    const data_aggregation = $scope.data_aggregations.find(da => da.id == $stateParams.data_aggregation_id)
                    if (data_aggregation) {
                        $scope.data_aggregation = data_aggregation
                        $scope.data_aggregation.column = all_columns.find(col => col.id == $scope.data_aggregation.column).displayName
                    } else {
                        $scope.data_aggregation = {'name': null, 'type': 'Average', 'column': null}
                    }
                    return $scope.data_aggregations
                }).then(data_aggregations => {
                    data_aggregations.forEach(data_aggregation => {
                        evaluate(data_aggregation.id)
                            .then(value => {
                                data_aggregation.value = value
                            })
                    })
                })
        }

        // const evaluate = (data_aggregation_id) => {
        //     return data_aggregation_service.evaluate($scope.organization.id, data_aggregation_id)
        //         .then(response => {
        //             return response.data
        //         })

        // }

        const init = () => {
            if (!$scope.data_aggregation){
                $scope.data_aggregation = { 'name': null, 'type': 'Average', 'column': null}
            }
            get_data_aggregations()
        };

        init();
    }
]);
