angular.module('BE.seed.controller.inventory_detail_timeline', [])
    .controller('inventory_detail_timeline_controller', [
        '$scope',
        '$stateParams',
        'inventory_payload',
        'events',
        'cycles',
        function (
            $scope,
            $stateParams,
            inventory_payload,
            events,
            cycles,
        ) {
            $scope.cycleNameById = cycles.cycles.reduce((acc, curr) => {
                return {...acc, [curr.id]: curr.name}
            }, {});
            $scope.events = events
            $scope.inventory_type = $stateParams.inventory_type;
            $scope.inventory = {
                view_id: $stateParams.view_id,
                related: $scope.inventory_type === 'properties' ? inventory_payload.taxlots : inventory_payload.properties
            };

            let expanded_rows = {
                'cycles': {},
                'events': {}
            }
            $scope.expand_row = (type, id) => {
                if(expanded_rows[type].hasOwnProperty(id)) {
                    expanded_rows[type][id] = !expanded_rows[type][id]
                } else {
                    expanded_rows[type][id] = true
                }
            }

            $scope.check_expanded_row = (cycle_id, event_id=null) => {
                if (event_id) {
                    return expanded_rows['cycles'][cycle_id] && expanded_rows['events'][event_id]
                } else {
                    return expanded_rows['cycles'][cycle_id]
                }
            }

            format_timeline = (events) => {
                let eventsByCycle = events.reduce((result, event) => {
                    if (!result[event.cycle]) {
                        result[event.cycle] = []
                    }
                    result[event.cycle].push(event)
                    return result
                }, {})
                $scope.timeline = eventsByCycle
            }
            format_timeline($scope.events.data)


        const atEvents = $scope.events.data.filter(e => e.event_type == "ATEvent");
        const scenarios = atEvents.reduce((acc, curr) => {
            return [...acc, ...curr.scenarios]
        },[]);

        $scope.measureGridOptionsByScenarioId = {}
        $scope.gridApiByScenarioId = {}
        scenarios.forEach(scenario => {
            measureGridOptions = {
                data: scenario.measures.map(measure => { return {
                    "category": measure.category,
                    "name": measure.name,
                    "recommended": measure.recommended,
                    "category_affected": measure.category_affected,
                    "cost_installation": measure.cost_installation,
                    "cost_material": measure.cost_material,
                    "cost_residual_value": measure.cost_residual_value,
                    "cost_total_first": measure.cost_total_first,
                    "cost_capital_replacement": measure.cost_capital_replacement,
                    "description": measure.description,
                    "useful_life": measure.useful_life

                }}),
                minRowsToShow: Math.min(scenario.measures.length, 10),
                onRegisterApi: function (gridApi) {
                    $scope.gridApiByScenarioId[scenario.id] = gridApi;
                }
            }
            $scope.measureGridOptionsByScenarioId[scenario.id] = measureGridOptions;
        })

        $scope.check_expanded_scenario = (index) => {
            const element = document.getElementById(`indicator-${index}`)
            const grandparent = element.parentNode.parentNode
            return grandparent.ariaExpanded == 'true'
        }

        $scope.resizeGridByScenarioId = (scenarioId) => {
            gridApi = $scope.gridApiByScenarioId[scenarioId]
            setTimeout(gridApi.core.handleWindowResize, 50);
        }
        }]);
