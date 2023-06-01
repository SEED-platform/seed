/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_editor_modal', [])
    .controller('ubid_editor_modal_controller', [
        '$scope',
        '$state',
        '$uibModalInstance',
        '$q',
        'ubid',
        'state_id',
        'view_id',
        'inventory_key',
        'ubid_service',
        function (
            $scope,
            $state,
            $uibModalInstance,
            $q,
            ubid,
            state_id,
            view_id,
            inventory_key,
            ubid_service,
        ) {
            $scope.ubid = ubid;
            $scope.state_id = state_id;
            let refresh = false;

            ubid_service.get_ubid_models_by_state(view_id, inventory_key).then(results => {
                $scope.ubids = results.data;
            })

            if (!ubid) {
                $scope.ubid = {
                    ubid: '',
                    preferred: false,
                };
                $scope.ubid[inventory_key] = state_id;
                $scope.update = false;
            } else {
                $scope.update = true;
            }

            $scope.toggle_preferred = () => {
                $scope.ubid.preferred = !$scope.ubid.preferred;
            }

            $scope.upsert_ubid = () => {
                refresh = true
                $scope.ubid.id ? update_ubid() : create_ubid();
            }

            const create_ubid = () => {
                if (check_existing()) {
                    return
                }

                ubid_service.validate_ubid($scope.ubid.ubid)
                    .then((result) => {
                        if (result.data.valid) {
                            $scope.invalid = false;
                            return ubid_service.create_ubid(inventory_key, state_id, $scope.ubid);
                        } else {
                            $scope.ubid_error = `"${result.data.ubid}" is not a valid UBID. Please Retry.`;
                            throw new Error('Invalid UBID')
                        }
                    })
                    .then(() => {
                        $scope.close()
                    })
                    .catch((error) => {
                        $scope.invalid = true
                    });
            }

            const update_ubid = () => {
                if (check_existing()) {
                    return
                }

                let ubids = [$scope.ubid]
                if ($scope.ubid.preferred) {
                    let preferred_ubids = $scope.ubids.filter(ubid => ubid.preferred && ubid.id != $scope.ubid.id);
                    preferred_ubids.forEach(ubid => ubid.preferred = false);
                    ubids = [...ubids, ...preferred_ubids];
                };

                let promises = [];
                ubids.forEach(ubid => {
                    const promise = ubid_service.update_ubid(ubid)
                    promises.push(promise)
                });
                $q.all(promises).then(() => {
                    $scope.close()
                });

            }

            const check_existing = () => {
                // If creating, check for matching ubids. If updating, exclude the current ubid (id)
                const existing_ubid = $scope.ubids.find(ubid => ubid.ubid === $scope.ubid.ubid && ubid.id !== $scope.ubid.id);
         
                if (existing_ubid) {
                    $scope.invalid = true;
                    $scope.ubid_error = `"${$scope.ubid.ubid}" is an existing UBID. Please Retry`;
                    return true;
                }
            }

            $scope.close = function () {
                $uibModalInstance.close({
                    refresh: refresh
                });
            };

        }
    ]
)
