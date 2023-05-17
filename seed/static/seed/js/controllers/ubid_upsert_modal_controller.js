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
            $scope.inventory_payload = inventory_payload;
            $scope.editing = false
            const reset_new_ubid = () => {
                $scope.creating = false
                $scope.new_ubid = { ubid: '', preferred: false }
            }

            const  view_id = property_view_id || taxlot_view_id;
            const inventory_type = property_view_id ? 'property' : 'taxlot';
            $scope.ubids = [];
            const refresh_ubids = () => {
                ubid_service.get_ubid_models_by_state(view_id, inventory_type).then(results => {
                    if ('data' in results){
                        $scope.ubids = results.data;
                    } else {
                        $scope.message = results.message;
                    }
                });
            }


            $scope.ubid_upsert_state = 'verify';
            $scope.create_ubid = () => {
                const state_id = inventory_payload.state.id
                if (inventory_type == 'property') {
                    ubid_service.create_ubid(inventory_type, state_id, $scope.new_ubid)
                }
                reset_new_ubid()
                refresh_ubids()
            }
            $scope.edit_ubids = () => {
                console.log('edit ubid')
                $scope.editing = true
            }
            $scope.delete_ubid = (ubid_id) => {
                console.log('delete ubid')
                ubid_service.delete_ubid(ubid_id)
                refresh_ubids()
            }
            $scope.update_ubid = (ubid) => {
                console.log('ubid: ', ubid.ubid)
                $scope.editing = false
            }
            $scope.update_preferred = (id, preferred) => {
                console.log('update preferred')
            }

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
            
            // init
            reset_new_ubid()
            refresh_ubids()
        }
    ]);
