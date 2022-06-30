/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_aggregation_modal', []).controller('data_aggregation_modal_controller', [
        '$scope',
        '$uibModalInstance',
        'all_columns',
        'data_aggregation_service',
        'organization',

        function (
            $scope,
            $uibModalInstance,
            all_columns,
            data_aggregation_service,
            organization,
        ) {
            $scope.all_columns = all_columns;
            $scope.organization = organization;
            $scope.crud_selection = 'overview';
            $scope.data_aggregation = {
                'name': null,
                'type': 'Average',
                'column': null,
            };
            $scope.data_aggregation_type_options = ['Average', 'Count', 'Max', 'Min', 'Sum'];

            $scope.validate_data_aggregation = () => {
                return Object.values($scope.data_aggregation).every(Boolean)
            };

            $scope.crud_select = (crud_option) => {
                $scope.crud_selection = crud_option
            };

            $scope.capitalize = (str) => {
                return str[0].toUpperCase() + str.slice(1);
            };

            $scope.create_data_aggregation = () => {
                let { name, type, column } = $scope.data_aggregation
                column = column.id
                data_aggregation_service.create_data_aggregation($scope.organization.id, {name, type, column})
                    .then(response => {
                        console.log(response)
                        $scope.crud_select('post_action')
                        get_data_aggregations()
                        if (response.status == 'success') {
                            $scope.message = `Successfully created Data Aggregation id:${response.data_aggregation.id} name: ${response.data_aggregation.name}`

                    } else {
                            $scope.message = `Error`
                        }
                    })
            };

            $scope.confirm_delete_data_aggregation = (data_aggregation_id) => {
                data_aggregation_service.get_data_aggregation($scope.organization.id, data_aggregation_id)
                .then(response => {
                    $scope.data_aggregation_to_delete = response.data_aggregation
                })
                $scope.crud_select('delete')
                
            }

            $scope.delete_data_aggregation = (data_aggregation_id) => {
                console.log('delete data agg', data_aggregation_id)
                data_aggregation_service.delete_data_aggregation($scope.organization.id, data_aggregation_id)
                    .then(response => {
                        console.log(response)
                        $scope.crud_select('post_action')
                        get_data_aggregations()
                        if (response.status == 'success') {
                            $scope.message = 'Successfully Deleted Data Aggregation'
                        } else {
                            $scope.message = `Error`
                        }
                    })
            }

            $scope.edit_data_aggregation = (data_aggregation_id) => {
                data_aggregation_service.get_data_aggregation($scope.organization.id, data_aggregation_id)
                    .then(response => {
                        $scope.data_aggregation = response.data_aggregation
                    })
                $scope.crud_select('update')
            }

            $scope.update_data_aggregation = (data_aggregation_id) => {
                console.log('delete data agg', data_aggregation_id)
                let { name, type, column } = $scope.data_aggregation
                column = column.id
                data_aggregation_service.update_data_aggregation($scope.organization.id, data_aggregation_id, {name, type, column})
                    .then(response => {
                        console.log(response)
                        $scope.crud_select('post_action')
                        get_data_aggregations()
                        if (response.status == 'success') {
                            $scope.message = `Successfully Updated Data Aggregation id:${response.data_aggregation.id} name: ${response.data_aggregation.name}`
                        } else {
                            $scope.message = `Error`
                        }
                    })

            }


            $scope.cancel =  () => {
                $uibModalInstance.dismiss();
            };

            const get_data_aggregations = () => {
                data_aggregation_service.get_data_aggregations($scope.organization.id)
                    .then(data => {
                        console.log('all data agg', data)
                        data.message.forEach(da => da.column_id_name = da.id + ' / ' + da.name)
                        $scope.data_aggregations = data.message

                    })
            }

            const init = () => {
                const x = 10
                get_data_aggregations()
                console.log('init modal')
            };

            init();
        }
    ]);