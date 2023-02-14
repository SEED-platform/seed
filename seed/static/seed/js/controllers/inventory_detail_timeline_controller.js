angular.module('BE.seed.controller.inventory_detail_timeline', [])
    .controller('inventory_detail_timeline_controller', [
        '$scope',
        '$stateParams',
        'inventory_payload',
        function (
            $scope,
            $stateParams,
            inventory_payload,
        ) {
            $scope.test = 'abcdefg';
            $scope.inventory_type = $stateParams.inventory_type;
            $scope.inventory = {
                view_id: $stateParams.view_id,
                related: $scope.inventory_type === 'properties' ? inventory_payload.taxlots : inventory_payload.properties
            };
            $scope.item_state = inventory_payload.state;
            $scope.scenario_expanded = {}
            $scope.expand_scenario = (scenario_id) => {
                if ($scope.scenario_expanded[scenario_id]) {
                    $scope.scenario_expanded[scenario_id] = !$scope.scenario_expanded[scenario_id]
                } else {
                    $scope.scenario_expanded[scenario_id] = true
                }

                console.log('CLICK!')
            }


        }])