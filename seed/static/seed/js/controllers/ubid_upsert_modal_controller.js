/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_upsert_modal', [])
    .controller('ubid_upsert_modal_controller', [
        '$scope',
        '$state',
        '$q',
        '$uibModalInstance',
        'property_view_id',
        'taxlot_view_id',
        'inventory_payload',
        'inventory_service',
        'ubid_service',
        function (
            $scope,
            $state,
            $q,
            $uibModalInstance,
            property_view_id,
            taxlot_view_id,
            inventory_payload,
            inventory_service,
            ubid_service,
        ) {
            $scope.inventory_payload = inventory_payload;
            $scope.editing = false;
            let refresh = false;
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
                refresh = true
                if ($scope.inventory_type == 'property') {
                    ubid_service.create_ubid($scope.inventory_type, state_id, $scope.new_ubid).then(() => {
                        reset_new_ubid();
                        refresh_ubids();
                    });
                }
            }
            $scope.cancel_edit = () => {
                $scope.editing = false;
                refresh_ubids();
            }
            
            $scope.delete_ubid = (ubid_id) => {
                ubid_service.delete_ubid(ubid_id).then(() => {
                    refresh = true
                    refresh_ubids()
                })
            }

            $scope.update_ubids = () => {
                refresh = true
                $scope.editing = false;
                let promises = [];
                $scope.ubids.forEach(ubid => {
                    const promise = ubid_service.update_ubid(ubid)
                    promises.push(promise)
                })
                $q.all(promises).then(() => {
                    refresh_ubids();
                });
            }


            /**
             * close: closes the modal
             */
            $scope.close = function () {
                refresh && $state.reload()
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
