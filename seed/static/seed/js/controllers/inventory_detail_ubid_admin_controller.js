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

        function (
            $scope,
            $state,
            ubid_service,
            simple_modal_service,
            $uibModal,
            urls,
        ) {
            // $scope.property_view_id is passed from modal. Will probably have to set it on the inv detail page
            const view_id = $scope.property_view_id || $scope.taxlot_view_id
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

            $scope.upsert_ubid = (ubid = false) => {
                console.log('upsert_ubid')
                $uibModal.open({
                    backdrop: 'static',
                    templateUrl: urls.static_url + 'seed/partials/ubid_editor_modal.html',
                    controller: 'ubid_editor_modal_controller',
                    resolve: {
          
                    }
                });
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