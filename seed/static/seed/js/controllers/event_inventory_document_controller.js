/*
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.event_inventory_document', [])
    .controller('event_inventory_document_controller', [
        '$scope',
        '$state',
        'analyses_service',
        'inventory_service',
        function (
            $scope,
            $state,
            analyses_service,
            inventory_service,
        ) {
            console.log('event inventory document controller')

            $scope.$watch('expanded_rows', () => {
                if ($scope.check_expanded_row('event', $scope.cycle.id, $scope.event.id)) {
                    init()
                }
            })

            const init = () => {
                // return analyses_service.get_analysis_for_org(analysis_id, $scope.org.id)
                    
                console.log('go fetch inventory documents for event', $scope.event.id)
            }
        }
    ])