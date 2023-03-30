/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_timeline', [])
    .controller('inventory_detail_timeline_controller', [
        '$scope',
        '$stateParams',
        '$timeout',
        'uiGridConstants',
        'cycles',
        'events',
        'inventory_payload',
        'urls',
        'users_payload',
        'organization_payload',
        function (
            $scope,
            $stateParams,
            $timeout,
            uiGridConstants,
            cycles,
            events,
            inventory_payload,
            urls,
            users_payload,
            organization_payload
        ) {
            $scope.organization = organization_payload.organization
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
            $scope.item_state = inventory_payload.state;
            $scope.orgUsers = users_payload.users
            $scope.show_at_scenario_actions = false
            $scope.orderDesc = false
            $scope.setDesc = (selection) => {
                if (selection === $scope.orderDesc) return;
                $scope.orderDesc = selection
                formatTimeline($scope.selectedEvents)
            }

            const formatTimeline = (events) => {
                let eventsByCycle = []
                events.sort((a, b) => $scope.orderDesc ?
                    new Date(a.modified) - new Date(b.modified) :
                    new Date(b.modified) - new Date(a.modified)
                )
                events.forEach(event => {
                    const index = eventsByCycle.findIndex(e => e.cycle == event.cycle)
                    if (index == -1) {
                        let entry = {cycle: event.cycle, cycle_end_date: event.cycle_end_date, events:[event]}
                        eventsByCycle.push(entry)
                    } else {
                        let element = eventsByCycle[index]
                        element.events.push(event)
                    }
                })

                eventsByCycle.sort((a,b) =>  $scope.orderDesc?
                    new Date(a.cycle_end_date) - new Date(b.cycle_end_date) :
                    new Date(b.cycle_end_date) - new Date(a.cycle_end_date)
                )

                // Preprocess total number of events by type
                for (const cycle of eventsByCycle) {
                  cycle.eventTotals = $scope.groupByEventType(cycle.events);
                }

                $scope.timeline = eventsByCycle;
            }

            const formatDuration = (start, end) => {
                if (!start || !end) {
                    return
                }
                const milliseconds = moment(end) - moment(start);
                const seconds = Math.floor(milliseconds / 1000);
                const minutes = Math.floor(seconds / 60);
                const hours = Math.floor(minutes / 60);
                const days = Math.floor(hours / 24);

                if (days) {
                    return days + ' days';
                } else if (hours) {
                    return hours + ' hours';
                } else if (minutes) {
                    return minutes + ' minutes'
                } else if (seconds) {
                    return seconds + ' seconds'
                } else {
                    return milliseconds + ' ms'
                }
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
                            "category": measure.category_display_name,
                            "name": measure.display_name,
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
                            "Updated": moment(note.updated).format('YYYY-MM-DD'),
                            "Text": note.text
                        }],
                        enableColumnMenus: false,
                        enableHorizontalScrollbar: uiGridConstants.scrollbars.NEVER,
                        enableSorting: false,
                        enableVerticalScrollbar: uiGridConstants.scrollbars.NEVER,
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
                                "Created": moment(analysis.created_at).format('YYYY-MM-DD'),
                                "Run Duration": formatDuration(analysis.start_time, analysis.end_time),
                                "Status": analysis.status
                            }
                        ],
                        enableColumnMenus: false,
                        enableHorizontalScrollbar: uiGridConstants.scrollbars.NEVER,
                        enableSorting: false,
                        enableVerticalScrollbar: uiGridConstants.scrollbars.NEVER,
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

            $scope.eventSelectGridOptions = {
                data: [
                    {
                        "Select All": "Notes",
                        "eventType": "NoteEvent"
                    },
                    {
                        "Select All": "Analyses",
                        "eventType": "AnalysisEvent"
                    },
                    {
                        "Select All": "AT Uploads",
                        "eventType": "ATEvent"
                    },
                ],
                columnDefs: [
                    {field: "eventType", visible: false},
                    {field: "Select All"}
                ],
                enableColumnMenus: false,
                enableHorizontalScrollbar: uiGridConstants.scrollbars.WHEN_NEEDED,
                enableVerticalScrollbar: uiGridConstants.scrollbars.NEVER,
                minRowsToShow: 3,
                onRegisterApi: (gridApi) => {
                    $scope.gridApiEventSelection = gridApi;
                    $scope.gridApiEventSelection.selection.on.rowSelectionChanged($scope, $scope.eventSelect)
                    $scope.gridApiEventSelection.selection.on.rowSelectionChangedBatch($scope, $scope.eventSelect)

                    init = true;
                    $scope.gridApiEventSelection.core.on.rowsRendered($scope, function () {
                        if (init) {
                            $scope.gridApiEventSelection.selection.selectAllRows();
                            init = false;
                        }
                    })
                }
            }

            $scope.resizeGridEventSelection = () => {
                gridApi = $scope.gridApiEventSelection
                setTimeout(gridApi.core.handleWindowResize, 1);
            }

            $scope.eventSelect = () => {
                const selectedEventTypes = $scope.gridApiEventSelection.selection.getSelectedRows().map(event => event.eventType)
                $scope.selectedEvents = events.data.filter(event => selectedEventTypes.includes(event.event_type))
                formatTimeline($scope.selectedEvents)
            }


            $scope.eventTypeLookup = {
                "NoteEvent": "Note",
                "AnalysisEvent": "Analysis",
                "ATEvent": "Audit Template File",
            }

            $scope.formatDate = (date) => moment(date).format('YYYY-MM-DD');

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

            $scope.eventIconLookup = {
                'Analyses': 'fa fa-bar-chart',
                'Audit Template Files': 'fa fa-bolt',
                'Notes': 'fa fa-sticky-note-o',
            }

            $scope.resizeGridByScenarioId = (scenarioId) => {
                gridApi = $scope.gridApiByScenarioId[scenarioId]
                setTimeout(gridApi.core.handleWindowResize, 50);
            }

            $scope.resizeGridByEventType = (event, resizeMeasures=false) => {
                if (event.event_type == 'NoteEvent') {
                    const gridApi = $scope.gridApiByNoteId[event.note.id]
                    if (gridApi) setTimeout(gridApi.core.handleWindowResize, 50);
                } else if (event.event_type == 'AnalysisEvent') {
                    const gridApi = $scope.gridApiByAnalysisId[event.analysis.id]
                    if (gridApi) setTimeout(gridApi.core.handleWindowResize, 50)
                } else if (resizeMeasures && event.event_type == 'ATEvent') {
                    event.scenarios.forEach(scenario => {
                        $scope.resizeGridByScenarioId(scenario.id)
                    })
                }
            }

            const getInventoryDisplayName = function (property_type) {
                let error = '';
                let field = property_type === 'property' ? $scope.organization.property_display_field : $scope.organization.taxlot_display_field;
                if (!(field in $scope.item_state)) {
                    error = `${field} does not exist`;
                    field = 'address_line_1';
                }
                if (!$scope.item_state[field]) {
                    error += `${error === '' ? '' : ' and default '}${field} is blank`;
                }
                $scope.inventory_name_error = error;
                $scope.inventory_name = $scope.item_state[field] ? $scope.item_state[field] : '';
            };

            $scope.accordionsCollapsed = true
            $scope.collapseAccordions = (collapseAll) => {
                $scope.accordionsCollapsed = collapseAll
                const action = collapseAll ? 'hide' : 'show'
                $('.cycle-collapse').collapse(action)
                $('.event-collapse').collapse(action)
                $('.scenario-collapse').collapse(action)

                // Without resizing ui-grids will appear empty
                if (action == 'show'){
                    $scope.selectedEvents.forEach(event => $scope.resizeGridByEventType(event, resizeMeasures=true))
                }
            }

            $scope.formatMeasureStatuses = (scenario) => {
                statuses = scenario.measures.reduce((acc, measure) => {
                    const status = measure.implementation_status
                    if (!acc[status]) {
                        acc[status] = 0
                    }
                    acc[status]++
                    return acc
                }, {})
                return statuses
            }


            // Initiate data population
            getInventoryDisplayName($scope.inventory_type === 'properties' ? 'property' : 'taxlot');
            setMeasureGridOptions()
            setNoteGridOptions()
            setAnalysisGridOptions()
        }
    ]
);
