/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.set_update_to_now_modal', []).controller('set_update_to_now_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'property_views',
    'taxlot_views',
    'inventory_service',
    'uploader_service',
    function(
        $scope,
        $state,
        $uibModalInstance,
        property_views,
        taxlot_views,
        inventory_service,
        uploader_service,

    ) {
        $scope.property_views = property_views;
        $scope.taxlot_views = taxlot_views;
        $scope.refresh_progress = {
            progress: 0,
            status_message: '',
        };
        $scope.refreshing = false

        $scope.set_update_to_now = function () {
            $scope.refreshing = true
            inventory_service.start_set_update_to_now()
            .then(data => {
                uploader_service.check_progress_loop(data.data.progress_key, 0, 1,
                    function () { $scope.refresh_page()},
                    function () { },
                    $scope.refresh_progress);
                return inventory_service.set_update_to_now(property_views, taxlot_views, data.data.progress_key);
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
