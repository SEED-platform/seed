angular.module('BE.seed.controller.inventory_detail_timeline', [])
    .controller('inventory_detail_timeline_controller', [
        '$scope',
        '$stateParams',
        'cycles',
        'events',
        'inventory_payload',
        'urls',
        'users_payload',
        function (
            $scope,
            $stateParams,
            cycles,
            events,
            inventory_payload,
            urls,
            users_payload,
        ) {
            $scope.static_url = urls.static_url;
            $scope.cycleNameById = cycles.cycles.reduce((acc, curr) => {
                return {...acc, [curr.id]: curr.name}
            }, {});
            $scope.events = events
            $scope.inventory_type = $stateParams.inventory_type;
            $scope.inventory = {
                view_id: $stateParams.view_id,
                related: $scope.inventory_type === 'properties' ? inventory_payload.taxlots : inventory_payload.properties
            };
            $scope.orgUsers = users_payload.users

            const formatTimeline = (events) => {
                let eventsByCycle = events.reduce((result, event) => {
                    if (!result[event.cycle]) {
                        result[event.cycle] = []
                    }
                    result[event.cycle].push(event)
                    return result
                }, {})
                $scope.timeline = eventsByCycle
            }

            const formatDuration = (start, end) => {
                return '10 seconds'
            }

            $scope.formatUser = (user_id) => {
                if (!user_id) {
                    return
                }
                const user = $scope.orgUsers.find(u => u.user_id == user_id)
                let userName = ''
                if (user.first_name && user.last_name) {
                    userName = `${user.first_name} ${user.last_name}`
                } else {
                    userName = user.email
                }
                return userName
            }

            const setMeasureGridOptions = () => {
                const atEvents = $scope.events.data.filter(e => e.event_type == "ATEvent");
                const scenarios = atEvents.reduce((acc, curr) => {
                    return [...acc, ...curr.scenarios]
                },[]);
        
                $scope.measureGridOptionsByScenarioId = {}
                $scope.gridApiByScenarioId = {}
                scenarios.forEach(scenario => {
                    const measureGridOptions = {
                        data: scenario.measures.map(measure => { return {
                            "category": measure.category,
                            "name": measure.name,
                            "recommended": measure.recommended,
                            "status": measure.implementation_status,
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
            }
            
            const setNoteGridOptions = () => {
                const noteEvents = $scope.events.data.filter(e => e.event_type == "NoteEvent")
                const notes = noteEvents.map(e => e.note)
                $scope.noteGridOptionsById = {}
                $scope.gridApiByNoteId = {}
                notes.forEach(note => {
                    const noteGridOptions = {
                        data: [{
                            "Updated": moment(note.updated).format('YYYY/MM/DD'),
                            "Text": note.text
                        }],
                        minRowsToShow: 1,
                        onRegisterApi: function (gridApi) {
                            $scope.gridApiByNoteId[note.id] = gridApi;
                        }
                    }
                    $scope.noteGridOptionsById[note.id] = noteGridOptions;
                    
                })
            }     

            const setAnalysisGridOptions = () => {
                const analysisEvents = $scope.events.data.filter(e => e.event_type == 'AnalysisEvent')
                const analyses = analysisEvents.map(e => e.analysis)
                $scope.analysisGridOptionsById = {}
                $scope.gridApiByAnalysisId = {}
                analyses.forEach(analysis => {
                    const analysisGridOptions = {
                        data: [
                            {
                                "Name": analysis.name,
                                "Service": analysis.service,
                                "Created": moment(analysis.created_at).format('YYYY/MM/DD'),
                                "Run Duration": formatDuration(analysis.start_time, analysis.end_time),
                                "Status": analysis.status
                            }
                        ],
                        minRowsToShow: 1,
                        onRegisterApi: (gridApi) => {
                            $scope.gridApiByAnalysisId[analysis.id] = gridApi;
                        }
                    }
                    $scope.analysisGridOptionsById[analysis.id] = analysisGridOptions;
                    if (!_.isEmpty(analysis.configuration)) {
                        $scope.analysisGridOptionsById[analysis.id]["Configuration"] = analysis.configuration
                    }
                })
            }

            


            $scope.eventTypeLookup = {
                "NoteEvent": "Note",
                "AnalysisEvent": "Analysis",
                "ATEvent": "Audit Template File",
            }

            $scope.formatDate = (date) => {
                return moment(date).format('YYYY/MM/DD')
            }

            $scope.groupByEventType = (events) => {
                let eventTypeCount = events.reduce((acc, cur) => {
                    let event_type = pluralize($scope.eventTypeLookup[cur.event_type])
                    if (!acc[event_type]) {
                        acc[event_type] = 0
                    }
                    acc[event_type] ++
                    return acc
                }, {});
                const sortedEventTypeCount = Object.fromEntries(Object.entries(eventTypeCount).sort())
                return sortedEventTypeCount

            }

            $scope.resizeGridByScenarioId = (scenarioId) => {
                gridApi = $scope.gridApiByScenarioId[scenarioId]
                setTimeout(gridApi.core.handleWindowResize, 50);
            }
            $scope.resizeGridByEventType = (event) => {
                if (event.event_type == 'NoteEvent') {
                    noteId = event.note.id
                    gridApi = $scope.gridApiByNoteId[noteId]
                    setTimeout(gridApi.core.handleWindowResize, 50);
                } else if (event.event_type == 'AnalysisEvent') {
                    analysisId = event.analysis.id
                    gridApi = $scope.gridApiByAnalysisId[analysisId]
                    setTimeout(gridApi.core.handleWindowResize, 50)
                }
            }

            // Initiate data population
            formatTimeline($scope.events.data)
            setMeasureGridOptions()
            setNoteGridOptions()
            setAnalysisGridOptions()
        }
    ]
);
