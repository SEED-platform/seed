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
            $scope.check_expanded_row = (type, cycle_id, event_id=null) => {
                if (type == 'cycle') {
                    return $scope.expanded_rows['cycles'][cycle_id]
                } else if (type == 'event') {
                    return $scope.expanded_rows['cycles'][cycle_id] && $scope.expanded_rows['events'][event_id]
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
            // const create_element = () => {

            //     const para = document.createElement("p");
            //     const node = document.createTextNode("This is new.");
            //     para.appendChild(node);
                
            //     const elements = document.getElementsByClassName("page_header_container");
            //     elements[0].appendChild(para);
            // }

            // create_element()

            // const insert_trigger = (id) => {


            //     const para = document.createElement("p")
            //     const node = document.createTextNode("event-child-" + id)
            //     para.appendChild(node);
                
            //     const element = document.getElementById('event-child-' + id)
            //     element.appendChild(para)
            //     console.log('extra for ',id)
            // }

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
                                'type': 1,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'id': 19,
                                'data': {
                                    'created': '2021-02-14T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_1.pdf'
                                }
                            },
                            {
                                'inventory_document': 2,
                                'type': 1,
                                'created': '2021-02-13T12:48:10.446652-08:00',
                                'id': 20,
                                'data': {
                                    'created': '2021-02-13T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_2.pdf'
                                }
                            },
                            {
                                'inventory_document': 3,
                                'type': 1,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'id': 21,
                                'created': '2021-02-14T12:48:10.446652-08:00',
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
                                'type': 1,
                                'created': '2022-02-14T12:48:10.446652-08:00',
                                'id': 22,
                                'data': {
                                    'created': '2022-02-14T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_4.pdf'
                                }
                            },
                            {
                                'inventory_document': 5,
                                'type': 1,
                                'created': '2022-02-13T12:48:10.446652-08:00',
                                'id': 23,
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
                                'type': 1,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'id': 23,
                                'data': {
                                    'created': '2021-02-14T12:48:10.446652-08:00',
                                    'file_type': 'pdf',
                                    'file_name': 'document_6.pdf'
                                }
                            },
                            {
                                'analysis': 1,
                                'type': 2,
                                'created': '2021-02-14T12:48:10.446652-08:00',
                                'id': 24,
                                'data': {
                                    
                                    "id": 192,
                                    "service": "EUI",
                                    "status": "Completed",
                                    "name": "eui2",
                                    "created_at": "2023-02-16T10:56:37.143083-08:00",
                                    "start_time": "2023-02-16T10:56:37.477828-08:00",
                                    "end_time": "2023-02-16T10:56:37.580090-08:00",
                                    "configuration": {},
                                    "parsed_results": {},
                                    "user": 1,
                                    "organization": 1,
                                    "number_of_analysis_property_views": 1,
                                    "views": [
                                        62
                                    ],
                                    "cycles": [
                                        10
                                    ],
                                    "highlights": [
                                        {
                                            "name": "Fractional EUI",
                                            "value": "56.62 kBtu/sqft"
                                        },
                                        {
                                            "name": "Annual Coverage",
                                            "value": "100%"
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ],
            };

           


        }]);