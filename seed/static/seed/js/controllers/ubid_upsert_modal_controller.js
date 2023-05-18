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
            const view_id = property_view_id || taxlot_view_id;
            $scope.inventory_type = property_view_id ? 'property' : 'taxlot';
            $scope.ubids = [];
            $scope.$watch('ubids', () => {
                $scope.num_preferred = $scope.ubids.filter(ubid => ubid.preferred).length
            })

            const refresh_ubids = () => {
                ubid_service.get_ubid_models_by_state(view_id, $scope.inventory_type).then(results => {
                    if ('data' in results){
                        $scope.ubids = results.data;
                    } else {
                        $scope.message = results.message;
                    }
                });
            }

            $scope.preferred_change = () => {
                $scope.num_preferred = $scope.ubids.filter(ubid => ubid.preferred).length
            }
            $scope.create_ubid = () => {
                const state_id = inventory_payload.state.id
                if ($scope.inventory_type == 'property') {
                    ubid_service.create_ubid($scope.inventory_type, state_id, $scope.new_ubid);
                }
                reset_new_ubid();
                refresh_ubids();
            }
            $scope.edit_ubid = () => {
                $scope.editing = true;
            }
            $scope.cancel_edit = () => {
                $scope.editing = false;
                refresh_ubids();
            }
            
            $scope.delete_ubid = (ubid_id) => {
                ubid_service.delete_ubid(ubid_id)
                refresh_ubids()
            }
            $scope.update_ubids = () => {
                $scope.editing = false;
                $scope.ubids.forEach(ubid => ubid_service.update_ubid(ubid));
                refresh_ubids();
            }


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
