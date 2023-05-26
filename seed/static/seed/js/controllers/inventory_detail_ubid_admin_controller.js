/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_ubid_admin', [])
    .controller('inventory_detail_ubid_admin_controller', [
        '$scope',
        '$state',
        'ubid_service',
        'simple_modal_service',
        '$uibModal',
        'urls',
        'inventory_service',
        function (
            $scope,
            $state,
            ubid_service,
            simple_modal_service,
            $uibModal,
            urls,
            inventory_service,
        ) {
            let inventory_payload;
            let state_id = 0;
            // $scope.property_view_id is passed from modal. Will probably have to set it on the inv detail page
            const view_id = $scope.property_view_id || $scope.taxlot_view_id
            const inventory_type = $scope.property_view_id ? 'property' : 'taxlot'
            if ($scope.property_view_id) promise = inventory_service.get_property(view_id);
            else if ($scope.taxlot_view_id) promise = inventory_service.get_taxlot(view_id);
            promise.then(result => {
                inventory_payload = result
                state_id = inventory_payload.state.id
            })
            let refresh = false

            const refresh_ubids = () => {
                ubid_service.get_ubid_models_by_state(view_id, $scope.inventory_type).then(results => {
                    if ('data' in results) {
                        $scope.ubids = results.data.sort((a, b) => {
                            return a.preferred ? -1 : 1
                        });
                        console.log($scope.ubids)
                    } else {
                        $scope.message = results.message;
                    }
                });
            }

            $scope.edit_or_create = (ubid=false) => {
                let ubid_editor_modal = $uibModal.open({
                    backdrop: 'static',
                    templateUrl: urls.static_url + 'seed/partials/ubid_editor_modal.html',
                    controller: 'ubid_editor_modal_controller',
                    resolve: {
                        ubid: function () {
                            return ubid
                        },
                        state_id: function() {
                            return state_id
                        },
                        view_id: function() {
                            return view_id
                        },
                        inventory_type: function() {
                            return inventory_type
                        }   
                    }
                });
                ubid_editor_modal.result.then((result) => {
                    result.refresh && refresh_ubids()
                })
            }

            $scope.delete_ubid = (ubid, ubid_id) => {
                const modalOptions = {
                    type: 'default',
                    okButtonText: 'Yes',
                    cancelButtonText: 'Cancel',
                    headerText: 'Are you sure?',
                    bodyText: `You're about to permanently delete the UBID "${ubid}". Would you like to continue?`
                };
                simple_modal_service.showModal(modalOptions).then(() => {
                    // user confirmed, delete it
                    ubid_service.delete_ubid(ubid_id).then(() => {
                        refresh = true
                        refresh_ubids()
                    }).catch((err) => {
                        console.log(`Error attempting to delete ubid id: ${ubid_id}`)
                        console.log('Error', err)
                    })
                }, () => {
                    // user cancels
                });
            }

            // init
            refresh_ubids()
        }
    ]
    )