/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.refresh_metadata_modal', []).controller('refresh_metadata_modal_controller', [
    '$http',
    '$scope',
    '$uibModalInstance',
    'ids',
    function(
        $http,
        $scope,
        $uibModalInstance,
        ids,
    ) {
        $scope.id_count = ids.length

        $scope.cancel = function() {
            $uibModalInstance.dismiss('cancel');
        }


    }]);