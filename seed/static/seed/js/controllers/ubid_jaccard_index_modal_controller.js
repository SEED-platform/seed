/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_jaccard_index_modal', [])
    .controller('ubid_jaccard_index_modal_controller', [
        '$scope',
        '$uibModalInstance',
        'property_view_ids',
        'taxlot_view_ids',
        'ubids',
        'ubid_service',
        function (
            $scope, 
            $uibModalInstance, 
            property_view_ids, 
            taxlot_view_ids, 
            ubids,
            ubid_service,
        ) {
            $scope.property_view_ids = _.uniq(property_view_ids);
            $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);
            $scope.ubids = ubids

            $scope.total_selected_count = $scope.property_view_ids.length + $scope.taxlot_view_ids.length;

            $scope.ubid_jaccard_state = 'verify'
            $scope.ubid1 = ubids[0]
            $scope.ubid2 = ubids[1]

            $scope.compare_ubids = () => {
                console.log('compare ubids')
                ubid_service.compare_ubids($scope.property_view_ids, $scope.taxlot_view_ids).then((result) => {
                    if (result.status == 'success'){
                        $scope.jaccard_index = parseFloat(parseFloat(result.data).toFixed(3))
                        $scope.ubid_jaccard_state = 'result'
                    } else {
                        $scope.ubid_jaccard_state = 'failure'
                    }

                })
            }

            /**
             * cancel: dismisses the modal
             */
            $scope.cancel = function () {
                $uibModalInstance.dismiss({
                    ubid_jaccard_state: $scope.ubid_jaccard_state,
                    property_view_ids: $scope.property_view_ids,
                    taxlot_view_ids: $scope.taxlot_view_ids
                });
            };

            /**
             * close: closes the modal
             */
            $scope.close = function () {
                $uibModalInstance.close({
                    ubid_jaccard_state: $scope.ubid_jaccard_state,
                    property_view_ids: $scope.property_view_ids,
                    taxlot_view_ids: $scope.taxlot_view_ids
                });
            };

            console.log('ubid modal jaccard index controller')
        }
    ]);
