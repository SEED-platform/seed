/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.refresh_metadata_modal', []).controller('refresh_metadata_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'ids',
    'property_states',
    'taxlot_states',
    'inventory_type',
    'inventory_service',
    'uploader_service',
    function(
        $scope,
        $state,
        $uibModalInstance,
        ids,
        property_states,
        taxlot_states,
        inventory_type,
        inventory_service,
        uploader_service,

    ) {
        const states = property_states || taxlot_states
        $scope.id_count = ids.length
        $scope.inventory_type = inventory_type
        $scope.refresh_progress = {
            progress: 0,
            status_message: '',
        };
        $scope.refreshing = false

        $scope.refresh_metadata = function () {
            $scope.refreshing = true
            inventory_service.start_refresh_metadata()
            .then(data => {
                uploader_service.check_progress_loop(data.data.progress_key, 0, 1,
                    function () { $scope.refresh_page()},
                    function () { },
                    $scope.refresh_progress);
                return inventory_service.refresh_metadata(ids, states, inventory_type, data.data.progress_key);
            })
        }

        $scope.refresh_page = function () {
            $state.reload();
            $uibModalInstance.dismiss('cancel');
        };

        $scope.cancel = function() {
            $uibModalInstance.dismiss('cancel');
        }
    }]);
