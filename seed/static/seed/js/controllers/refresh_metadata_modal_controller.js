/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.refresh_metadata_modal', []).controller('refresh_metadata_modal_controller', [
    '$http',
    '$scope',
    '$uibModalInstance',
    'ids',
    'inventory_type',
    'inventory_service',
    function(
        $http,
        $scope,
        $uibModalInstance,
        ids,
        inventory_type,
        inventory_service,

    ) {
        $scope.id_count = ids.length
        $scope.inventory_type = inventory_type

        $scope.refresh_metadata = function () {
            console.log('refresh data for ',inventory_type, ': ', ids)
            inventory_service.refresh_metadata(ids, inventory_type)
        }

        $scope.cancel = function() {
            $uibModalInstance.dismiss('cancel');
        }


    }]);