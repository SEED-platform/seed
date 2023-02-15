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
            $scope.expanded_rows = {
                'cycles': {},
                'events': {},
            }
            $scope.expand_row = (type, id) => {
                if ($scope.expanded_rows[type][id]) {
                    $scope.expanded_rows[type][id] = !$scope.expanded_rows[type][id]
                } else {
                    $scope.expanded_rows[type][id] = true
                }
            }

            $scope.format_created = (date) => {
                return moment(date).format('YYYY/MM/DD')
            }

            $scope.format_event_type = (event) => {
                if (event.hasOwnProperty('inventory_document')) {
                    return 'Inventory Document'
                } else if (event.hasOwnProperty('analysis')) {
                    return 'Analysis'
                }
                return event.id
            }

            // DUMMY DATA FOR TESTING
            // ----------------------
            // events are only returned for a specified property
            $scope.timeline = {
                'property': 9, 
                'cycles': [
                    {
                        'id': 21,
                        'cycle_name': 'c2021',
                        'events': [
                            {
                                'inventory_document': 1,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'id': 19,
                                'property': 9,
                                'data': {
                                    'created': '2021-02-14T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_1.pdf'
                                }
                            },
                            {
                                'inventory_document': 2,
                                'created': '2021-02-13T12:48:10.446652-08:00',
                                'id': 20,
                                'property': 9,
                                'data': {
                                    'created': '2021-02-13T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_2.pdf'
                                }
                            },
                            {
                                'inventory_document': 3,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'id': 21,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'property': 9,
                                'data': {
                                    'created': '2021-02-14T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_3.pdf'
                                }
                            },
                        ],
                    },
                    {
                        'id': 22,
                        'cycle_name': 'c2022',
                        'events': [
                            {
                                'inventory_document': 4,
                                'created': '2022-02-14T12:48:10.446652-08:00',
                                'cycle': 29,
                                'cycle_name': 'c2022',
                                'id': 22,
                                'property': 9,
                                'data': {
                                    'created': '2022-02-14T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_4.pdf'
                                }
                            },
                            {
                                'inventory_document': 5,
                                'created': '2022-02-13T12:48:10.446652-08:00',
                                'cycle': 29,
                                'cycle_name': 'c2022',
                                'id': 23,
                                'property': 9,
                                'data': {
                                    'created': '2022-02-13T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_5.pdf'
                                }
                            },
                        ]
                    },
                    {
                        'id': 23,
                        'cycle_name': 'c2023',
                        'events': [
                            {
                                'inventory_document': 6,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'cycle': 30,
                                'cycle_name': 'c2021',
                                'id': 24,
                                'property': 9,
                                'data': {
                                    'created': '2021-02-14T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_6.pdf'
                                }
                            }
                        ]
                    }
                ],
            };


        }]);