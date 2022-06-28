/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_aggregation_modal', []).controller('data_aggregation_modal_controller', [
        '$scope',
        '$uibModalInstance',
        function (
            $scope,
            $uibModalInstance,
        ) {
            $scope.crud_selection = 'create'

            $scope.crud_select = function(crud_option) {
                $scope.crud_selection = crud_option
            }
            $scope.start = function() {
                console.log('start')
            }

            $scope.cancel = function () {
                $uibModalInstance.dismiss();
            };
        }
    ]);