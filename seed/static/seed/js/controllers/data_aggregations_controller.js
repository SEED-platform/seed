/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_aggregations', []).controller('data_aggregations_controller', [
    '$scope',
    '$stateParams',
    '$state',
    'all_columns',
    '$uibModal',
    'urls',
    'organization_payload',
    'data_aggregation_service',
    'simple_modal_service',
    'Notification',
    function (
        $scope,
        $stateParams,
        $state,
        all_columns,
        $uibModal,
        urls,
        organization_payload,
        data_aggregation_service,
        simple_modal_service,
        Notification,
    ) {
        $scope.organization = organization_payload.organization;
        $scope.inventory_type = $stateParams.inventory_type;
        $scope.open_data_aggregation_modal = function () {
            console.log('data agg click')
            $uibModal.open({
                backdrop: 'static',
                templateUrl: urls.static_url + 'seed/partials/data_aggregation_modal.html',
                controller: 'data_aggregation_modal_controller',
                resolve: {
                    all_columns: function () {
                        return all_columns
                    },
                    organization: function () {
                        return organization_payload.organization
                    }
                }
            });
        }

        const get_data_aggregations = () => {
            data_aggregation_service.get_data_aggregations($scope.organization.id)
                .then(response => {
                    response.message.forEach(data_aggregation => {
                        column = all_columns.find(column => column.id == data_aggregation.column)
                        data_aggregation.column_id_name = column.id + ' / ' + column.displayName
                    })
                    $scope.data_aggregations = response.message
                    return $scope.data_aggregations
                }).then(data_aggregations => {
                    data_aggregations.forEach(data_aggregation => {
                        evaluate(data_aggregation.id)
                            .then(value => {
                                data_aggregation.value = value
                            })
                    })
                })

            $scope.data_aggregation = {
                'name': null,
                'type': 'Average',
                'column': null,
            };
        }

        const evaluate = (data_aggregation_id) => {
            return data_aggregation_service.evaluate($scope.organization.id, data_aggregation_id)
                .then(response => {
                    return response.data
                })
        }

        $scope.edit_data_aggregation = function (data_aggregation_id) {
            $state.go('data_aggregation_editor', { inventory_type: $scope.inventory_type, data_aggregation_id });
        };


        $scope.delete_data_aggregation = function (data_aggregation_id) {
            const data_aggregation = $scope.data_aggregations.find(da => da.id == data_aggregation_id);

            const modalOptions = {
                type: 'default',
                okButtonText: 'Yes',
                cancelButtonText: 'Cancel',
                headerText: 'Are you sure?',
                bodyText: `You're about to permanently delete the data aggregation "${data_aggregation.name}". Would you like to continue?`
            };
            simple_modal_service.showModal(modalOptions).then(() => {
                //user confirmed, delete it
                data_aggregation_service.delete_data_aggregation($scope.organization.id, data_aggregation_id)
                    .then(() => {
                        Notification.success(`Deleted "${data_aggregation.name}"`);
                        get_data_aggregations().then(location.reload())
                    })
                    .catch(err => {
                        $log.error(err);
                        if (err.data.detail == 'Cannot delete protected objects while related objects still exist') {
                            Notification.error(`Cannot delete Data Aggregation "${data_aggregation.name}".`);
                        } else {
                            Notification.error(`Error attempting to delete "${data_aggregation.name}". Please refresh the page and try again.`);
                        }
                    });
            }, () => {
                //user doesn't want to
            });
        };

        const init = () => {
            get_data_aggregations()
        };

        init();

    }
]);
