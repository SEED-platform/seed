/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_upsert_modal', [])
    .controller('ubid_upsert_modal_controller', [
        '$scope',
        '$uibModalInstance',
        'property_view_id',
        'taxlot_view_id',
        'inventory_payload',
        'inventory_service',
        'ubid_service',
        function (
            $scope,
            $uibModalInstance,
            property_view_id,
            taxlot_view_id,
            inventory_payload,
            inventory_service,
            ubid_service,
        ) {
            // $scope.property_view_ids = property_view_id;
            // $scope.taxlot_view_ids = taxlot_view_id;
            $scope.inventory_payload = inventory_payload

            // $scope.x 
            // inventory_service.get_property(property_view_id).then(res => {
            //     console.log('get prop')
            // })

            $scope.ubid_upsert_state = 'verify'

            /**
             * cancel: dismisses the modal
             */
            $scope.cancel = function () {
                $uibModalInstance.dismiss({
                    ubid_jaccard_state: $scope.ubid_upsert_state,
                    property_view_ids: $scope.property_view_ids,
                    taxlot_view_ids: $scope.taxlot_view_ids
                });
            };

            /**
             * close: closes the modal
             */
            $scope.close = function () {
                $uibModalInstance.close({
                    ubid_upsert_state: $scope.ubid_upsert_state,
                    property_view_ids: $scope.property_view_ids,
                    taxlot_view_ids: $scope.taxlot_view_ids
                });
            };

            console.log('ubid modal jaccard index controller')
        }
    ]);
