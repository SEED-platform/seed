/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_aggregation_modal', []).controller('data_aggregation_modal_controller', [
        '$scope',
        '$uibModalInstance',
        'all_columns',
        function (
            $scope,
            $uibModalInstance,
            all_columns,
        ) {
            $scope.all_columns = all_columns
            $scope.crud_selection = 'create'
            $scope.new_data_aggregation = {
                'name': null,
                'type': null,
                'column': null,
            }
            $scope.data_aggregation_type_options = ['Average', 'Count', 'Max', 'Min', 'Sum']

            $scope.validate_new_data_aggregation = function() {
                console.log($scope.new_data_aggregation)
                return Object.values($scope.new_data_aggregation).every(Boolean)
            }

            $scope.crud_select = function(crud_option) {
                $scope.crud_selection = crud_option
            }
            $scope.create = function() {
                console.log('create')
            }

            $scope.cancel = function () {
                $uibModalInstance.dismiss();
            };

            const init = function() {
                const x = 10
            }
            init()
        }
    ]);