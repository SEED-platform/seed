/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_aggregation_modal', []).controller('data_aggregation_modal_controller', [
        '$scope',
        function (
            $scope
        ) {
            $scope.x = 10;
            $scope.cancel = function() {
                console.log('cancel')
            }
            $scope.start = function() {
                console.log('start')
            }
            $scope.refresh = function() {
                console.log('refresh')
            }
        }
    ]);