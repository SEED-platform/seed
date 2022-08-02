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
        // $scope.dog = $stateParams.dog;
        // $scope.param2 = $stateParams.param2;

        $scope.all_columns = all_columns;
        $scope.organization = organization_payload.organization;
        // $scope.crud_selection = 'overview';

        $scope.data_aggregation_type_options = ['Average', 'Count', 'Max', 'Min', 'Sum'];

        $scope.validate_data_aggregation = () => {
            return Object.values($scope.data_aggregation).every(Boolean)
        };

        // $scope.crud_select = (crud_option) => {
        //     $scope.crud_selection = crud_option
        // };

        $scope.capitalize = (str) => {
            return str[0].toUpperCase() + str.slice(1);
        };

        $scope.create_data_aggregation = () => {
            let { name, type, column } = $scope.data_aggregation
            return data_aggregation_service.create_data_aggregation($scope.organization.id, { name, type, column })
                // .then(response => {
                //     get_data_aggregations()
                //     if (response.status == 'success') {
                //         $scope.message = `Successfully created Data Aggregation id:${response.data_aggregation.id} name: ${response.data_aggregation.name}`
                //     } else {
                //         $scope.message = `Error`
                //     }
                // })
        };

        $scope.create_or_update_data_aggregation = () => {
            let api_call = null;
            const creating = !$scope.data_aggregation.id;

            spinner_utility.show();
            if (creating) {
                console.log('>>> CREATE')
                api_call = () => $scope.create_data_aggregation();
            } else {
                console.log('>>> UPDATE')
                api_call = () => $scope.update_data_aggregation();
            };

            api_call()
                .then(res => {
                    spinner_utility.hide();
                    modified_service.resetModified();
                    Notification.success(`${creating ? 'Created' : 'Updated'} "${res.data_aggregation.name}"`);
                    $state.go('data_aggregations', { inventory_type: 'properties' });
                }).catch(err => {
                    spinner_utility.hide();
                    $log.error(err);
                    if (err.data && err.data.errors) {
                        $scope.errors_from_server = err.data.errors;
                    } else {
                        throw Error(`Something unexpectedly went wrong: ${err}`);
                    }
                });
            
        }
        // $scope.confirm_delete_data_aggregation = (data_aggregation_id) => {
        //     data_aggregation_service.get_data_aggregation($scope.organization.id, data_aggregation_id)
        //         .then(response => {
        //             $scope.data_aggregation_to_delete = response.data_aggregation
        //         })
        //     $scope.crud_select('delete')

        // }

        // $scope.delete_data_aggregation = (data_aggregation_id) => {
        //     data_aggregation_service.delete_data_aggregation($scope.organization.id, data_aggregation_id)
        //         .then(response => {
        //             $scope.crud_select('post_action')
        //             get_data_aggregations()
        //             if (response.status == 'success') {
        //                 $scope.message = 'Successfully Deleted Data Aggregation'
        //             } else {
        //                 $scope.message = `Error`
        //             }
        //         })
        // }

        // $scope.edit_data_aggregation = (data_aggregation_id) => {
        //     data_aggregation_service.get_data_aggregation($scope.organization.id, data_aggregation_id)
        //         .then(response => {
        //             $scope.data_aggregation = response.data_aggregation
        //             $scope.data_aggregation.column = all_columns.find(c => c.id == $scope.data_aggregation.column)
        //         })
        //     $scope.crud_select('update')
        // }

        $scope.update_data_aggregation = () => {
            let { name, type, column } = $scope.data_aggregation
            return data_aggregation_service.update_data_aggregation($scope.organization.id, $scope.data_aggregation.id, { name, type, column })
                // .then(response => {
                //     return get_data_aggregations()
                //     if (response.status == 'success') {
                //         $scope.message = `Successfully Updated Data Aggregation id:${response.data_aggregation.id} name: ${response.data_aggregation.name}`
                //     } else {
                //         $scope.message = `Error`
                //     }
                // })
        }


        // $scope.cancel = () => {
        //     $uibModalInstance.dismiss();
        // };

        const get_data_aggregations = () => {
            data_aggregation_service.get_data_aggregations($scope.organization.id)
                .then(response => {
                    response.message.forEach(da => {
                        column = all_columns.find(c => c.id == da.column)
                        da.column_id_name = column.id + ' / ' + column.displayName
                    })
                    $scope.data_aggregations = response.message
                    $scope.data_aggregation = $scope.data_aggregations.find(da => da.id == $stateParams.data_aggregation_id)
                    return $scope.data_aggregations
                }).then(data_aggregations => {
                    data_aggregations.forEach(data_aggregation => {
                        evaluate(data_aggregation.id)
                            .then(value => {
                                data_aggregation.value = value
                            })
                    })
                })
            
                

                $scope.data_aggregation ? null :
                    $scope.data_aggregation = {
                        'name': null,
                        'type': 'Average',
                        'column': null,
                    };

                console.log('data_aggregation', $scope.data_aggregation)
        }

        // const evaluate = (data_aggregation_id) => {
        //     return data_aggregation_service.evaluate($scope.organization.id, data_aggregation_id)
        //         .then(response => {
        //             return response.data
        //         })

        // }

        const init = () => {
            get_data_aggregations()
        };

        init();
    }
]);
