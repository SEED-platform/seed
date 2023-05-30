/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_admin_modal', [])
    .controller('ubid_admin_modal_controller', [
        '$scope',
        '$state',
        'urls',
        '$uibModalInstance',
        'property_view_id',
        'taxlot_view_id',
        'inventory_payload',
        function (
            $scope,
            $state,
            urls,
            $uibModalInstance,
            property_view_id,
            taxlot_view_id,
            inventory_payload,
        ) {
            $scope.inventory_payload = inventory_payload;
            $scope.urls = urls;
            $scope.property_view_id = property_view_id;
            $scope.taxlot_view_id = taxlot_view_id;
            $scope.inventory_type = property_view_id ? 'property' : 'taxlot';
            let reload = false
            $scope.$on('callReload', () => {
                console.log('reload = ', true)
                reload = true
            })

            $scope.close = function () {
                reload && $state.reload()
                $uibModalInstance.close({

                });
            };

        }
    ]
)