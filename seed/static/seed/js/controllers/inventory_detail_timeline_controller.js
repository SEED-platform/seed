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

            $scope.format_created = (date) => {
                return moment(date).format('YYYY/MM/DD')
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

            // DUMMY DATA FOR TESTING
            // ----------------------
            // events are only returned for a specified property
        //     $scope.timeline = {
        //         'property': 9,
        //         'cycles': [
        //             {
        //                 'id': 21,
        //                 'cycle_name': 'c2021',
        //                 'events': [
        //                     {
        //                         'inventory_document': 1,
        //                         'type': 1,
        //                         'created': '2021-02-14T12:48:10.446652-08:00',
        //                         'id': 19,
        //                         'data': {
        //                             'created': '2021-02-14T12:48:10.446652-08:00',
        //                             'file_type': 'pdf',
        //                             'file_name': 'document_1.pdf'
        //                         }
        //                     },
        //                     {
        //                         'inventory_document': 2,
        //                         'type': 1,
        //                         'created': '2021-02-13T12:48:10.446652-08:00',
        //                         'id': 20,
        //                         'data': {
        //                             'created': '2021-02-13T12:48:10.446652-08:00',
        //                             'file_type': 'pdf',
        //                             'file_name': 'document_2.pdf'
        //                         }
        //                     },
        //                     {
        //                         'inventory_document': 3,
        //                         'type': 1,
        //                         'created': '2021-02-14T12:48:10.446652-08:00',
        //                         'id': 21,
        //                         'created': '2021-02-14T12:48:10.446652-08:00',
        //                         'data': {
        //                             'created': '2021-02-14T12:48:10.446652-08:00',
        //                             'file_type': 'pdf',
        //                             'file_name': 'document_3.pdf'
        //                         }
        //                     },
        //                 ],
        //             },
        //             {
        //                 'id': 22,
        //                 'cycle_name': 'c2022',
        //                 'events': [
        //                     {
        //                         'inventory_document': 4,
        //                         'type': 1,
        //                         'created': '2022-02-14T12:48:10.446652-08:00',
        //                         'id': 22,
        //                         'data': {
        //                             'created': '2022-02-14T12:48:10.446652-08:00',
        //                             'file_type': 'pdf',
        //                             'file_name': 'document_4.pdf'
        //                         }
        //                     },
        //                     {
        //                         'inventory_document': 5,
        //                         'type': 1,
        //                         'created': '2022-02-13T12:48:10.446652-08:00',
        //                         'id': 23,
        //                         'data': {
        //                             'created': '2022-02-13T12:48:10.446652-08:00',
        //                             'file_type': 'pdf',
        //                             'file_name': 'document_5.pdf'
        //                         }
        //                     },
        //                 ]
        //             },
        //             {
        //                 'id': 23,
        //                 'cycle_name': 'c2023',
        //                 'events': [
        //                     {
        //                         'inventory_document': 6,
        //                         'type': 1,
        //                         'created': '2021-02-14T12:48:10.446652-08:00',
        //                         'id': 23,
        //                         'data': {
        //                             'created': '2021-02-14T12:48:10.446652-08:00',
        //                             'file_type': 'pdf',
        //                             'file_name': 'document_6.pdf'
        //                         }
        //                     },
        //                     {
        //                         'analysis': 1,
        //                         'type': 2,
        //                         'created': '2021-02-14T12:48:10.446652-08:00',
        //                         'id': 24,
        //                         'data': {
        //                             "id": 192,
        //                             "service": "EUI",
        //                             "status": "Completed",
        //                             "name": "eui2",
        //                             "created_at": "2023-02-16T10:56:37.143083-08:00",
        //                             "start_time": "2023-02-16T10:56:37.477828-08:00",
        //                             "end_time": "2023-02-16T10:56:37.580090-08:00",
        //                             "configuration": {},
        //                             "parsed_results": {},
        //                             "user": 1,
        //                             "organization": 1,
        //                             "number_of_analysis_property_views": 1,
        //                             "views": [
        //                                 62
        //                             ],
        //                             "cycles": [
        //                                 10
        //                             ],
        //                             "highlights": [
        //                                 {
        //                                     "name": "Fractional EUI",
        //                                     "value": "56.62 kBtu/sqft"
        //                                 },
        //                                 {
        //                                     "name": "Annual Coverage",
        //                                     "value": "100%"
        //                                 }
        //                             ]
        //                         }
        //                     }
        //                 ]
        //             }
        //         ],
        //     };

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

        $scope.resizeGridByScenarioId = (scenarioId) => {
            gridApi = $scope.gridApiByScenarioId[scenarioId]
            setTimeout(gridApi.core.handleWindowResize, 50);
        }
        }]);
