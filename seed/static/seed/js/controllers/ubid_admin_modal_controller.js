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
            $scope.urls = urls
            $scope.modal_text = 'UBID ADMIN MODAL';
            $scope.parent_text = 'this is from the parent'
            $scope.property_view_id = property_view_id
            $scope.taxlot_view_id = taxlot_view_id
            $scope.inventory_type = property_view_id ? 'property' : 'taxlot';
            console.log('type', $scope.inventory_type)
            console.log('view', $scope.property_view_id)

            $scope.close = function () {
                $state.reload()
                // refresh && $state.reload()
                $uibModalInstance.close({

                });
            };

        }
    ]
)