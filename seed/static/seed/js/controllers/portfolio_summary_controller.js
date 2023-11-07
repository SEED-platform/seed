/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.portfolio_summary', [])
    .controller('portfolio_summary_controller', [
        '$scope',
        '$state',
        '$stateParams',
        'inventory_service',
        'label_service',
        'cycles',
        'organization_payload',
        'access_level_tree',
        'property_columns',
        'spinner_utility',
        'uiGridConstants',
        'gridUtil',
        function (
            $scope,
            $state,
            $stateParams,
            inventory_service,
            label_service,
            cycles,
            organization_payload,
            access_level_tree,
            property_columns,
            spinner_utility,
            uiGridConstants,
            gridUtil,
        ) {
            $scope.cycles = cycles.cycles;
            $scope.columns = property_columns;
            const goal_column_names = [
                'energy_score',
                'site_eui', 
                'site_eui_weather_normalized',
                'total_ghg_emissions_intensity'
            ]
            $scope.goal_columns = $scope.columns.filter(c => goal_column_names.includes(c.column_name))
            const matching_column_names = $scope.columns.filter(col => col.is_matching_criteria).map(col => col.column_name)
            $scope.valid = false;
            $scope.data = [];
            $scope.summary_data = [];
            $scope.organization = organization_payload.organization;
            $scope.access_level_tree = access_level_tree.access_level_tree;
            $scope.level_names = access_level_tree.access_level_names;
            const localStorageLabelKey = `grid.properties.labels`;

            
            /* Build out access_level_instances_by_depth recurrsively */
            let access_level_instances_by_depth = {};
            const calculate_access_level_instances_by_depth = function (tree, depth = 1) {
                if (tree == undefined) return;
                if (access_level_instances_by_depth[depth] == undefined) access_level_instances_by_depth[depth] = [];
                tree.forEach(ali => {
                    access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name })
                    calculate_access_level_instances_by_depth(ali.children, depth + 1);
                })
            }
            calculate_access_level_instances_by_depth($scope.access_level_tree, 1)
            
            $scope.change_selected_level_index = function () {
                new_level_instance_depth = parseInt($scope.portfolioSummary.level_name_index) + 1
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth]
            }

            // must be alphabetical
            const cycle_column_keys = ['energy_score', 'gross_floor_area', 'site_eui'].sort()
            const cycle_column_vals = property_columns.filter(c => cycle_column_keys.includes(c.column_name)).map(c => c.name)
            // convert column_name to name
            const cycle_column_lookup = Object.fromEntries(_.zip(cycle_column_keys, cycle_column_vals))

            const site_eui_column = property_columns.find(col => col.column_name == 'site_eui');
            $scope.portfolioSummary = {
                // temp - hardcoded
                name: 'Test Portfolio',
                goal_column: 'site_eui',
                goal: 0,
                starting_cycle: $scope.cycles.find(c => c.id == 3),
                ending_cycle: $scope.cycles.find(c => c.id == 2),
                // level_name_index
                // access_level_instance
            };


            const set_goal_fns = () => {
                switch ($scope.portfolioSummary.goal_column) {
                    case 'site_eui':
                        // format_properties()
                        $scope.goal_fn = set_site_eui_goal
                        // selected_columns()
                        //format_summary()
                        break
                }
            }

            $scope.refresh_data = () => {
                console.log('refresh_data')
                expected_keys = ['starting_cycle', 'ending_cycle', 'goal', 'goal_column', 'level_name_index', 'access_level_instance']
                valid = expected_keys.every(key => key in $scope.portfolioSummary)
                if (!valid) {
                    console.log('not valid')
                    return
                }
                set_goal_fns()
                console.log($scope.portfolioSummary)
                spinner_utility.show()
                const cycle_ids = [$scope.portfolioSummary.starting_cycle.id, $scope.portfolioSummary.ending_cycle.id]
                
                inventory_service.properties_cycle(undefined, cycle_ids).then(result => {
                    get_all_labels()
                    set_grid_options(result)
                    set_summary_grid_options()
                    // $scope.updateHeight()
                }).then(() => { 
                    $scope.valid = true;
                    spinner_utility.hide() 
                })
            }
            $scope.refresh_data()



            

            const percentage = (a, b) => {
                return Math.round((a - b) / a * 100)
            }

            // -------------- LABEL LOGIC -------------

            $scope.max_label_width = 750;
            $scope.get_label_column_width = (labels_col, key) => {
                if (!$scope.show_full_labels[key]) {
                    return 30;
                }
                // return 200;
                let maxWidth = 0;
                const renderContainer = document.body.getElementsByClassName('ui-grid-render-container-body')[1];
                const col = $scope.gridApi.grid.getColumn(labels_col);
                const cells = renderContainer.querySelectorAll(`.${uiGridConstants.COL_CLASS_PREFIX}${col.uid} .ui-grid-cell-contents`);
                Array.prototype.forEach.call(cells, (cell) => {
                    gridUtil.fakeElement(cell, {}, (newElm) => {
                        const e = angular.element(newElm);
                        e.attr('style', 'float: left;');
                        const width = gridUtil.elementWidth(e);
                        if (width > maxWidth) {
                            maxWidth = width;
                        }
                    });
                });
                return maxWidth > $scope.max_label_width ? $scope.max_label_width : maxWidth + 2;
            };

            // Expand or contract labels col
            $scope.show_full_labels = { start: false, end: false }
            $scope.toggle_labels = (labels_col, key) => {
                $scope.show_full_labels[key] = !$scope.show_full_labels[key];
                setTimeout(() => {
                    $scope.gridApi.grid.getColumn(labels_col).width = $scope.get_label_column_width(labels_col, key);
                    const icon = document.getElementById(`label-header-icon-${key}`);
                    icon.classList.add($scope.show_full_labels[key] ? 'fa-chevron-circle-left' : 'fa-chevron-circle-right');
                    icon.classList.remove($scope.show_full_labels[key] ? 'fa-chevron-circle-right' : 'fa-chevron-circle-left');
                    $scope.gridApi.grid.refresh();
                }, 0);
            };

            // retreive labels for cycle
            const get_all_labels = () => {
                get_labels('start');
                get_labels('end');
            }
            const get_labels = (key) => {
                const cycle = key == 'start' ? $scope.portfolioSummary.starting_cycle : $scope.portfolioSummary.ending_cycle;

                label_service.get_labels('properties', undefined, cycle.id).then((current_labels) => {                    
                    let labels = _.filter(current_labels, (label) => !_.isEmpty(label.is_applied));

                    // load saved label filter
                    const ids = inventory_service.loadSelectedLabels(localStorageLabelKey);
                    // $scope.selected_labels = _.filter(labels, (label) => _.includes(ids, label.id));
                    
                    if (key == 'start') {
                        $scope.starting_labels = labels
                        $scope.build_labels(key, $scope.starting_labels);
                    } else {
                        $scope.ending_labels = labels
                        $scope.build_labels(key, $scope.ending_labels);
                    }
                });
            };

            // Find labels that should be displayed and organize by applied inventory id
            $scope.show_labels_by_inventory_id = {start: {}, end: {}};
            $scope.build_labels = (key, labels) => {
                $scope.show_labels_by_inventory_id[key] = {};
                for (const n in labels) {
                    const label = labels[n];
                    if (label.show_in_list) {
                        for (const m in label.is_applied) {
                            const id = label.is_applied[m];
                            const property_id = $scope.property_lookup[id]
                            if (!$scope.show_labels_by_inventory_id[key][property_id]) {
                                $scope.show_labels_by_inventory_id[key][property_id] = [];
                            }
                            $scope.show_labels_by_inventory_id[key][property_id].push(label);
                        }
                    }
                }
            };

            // Builds the html to display labels associated with this row entity
            $scope.display_labels = (entity, key) => {
                const id =  entity.id;
                const labels = [];
                const titles = [];
                if ($scope.show_labels_by_inventory_id[key][id]) {
                    for (const i in $scope.show_labels_by_inventory_id[key][id]) {
                        const label = $scope.show_labels_by_inventory_id[key][id][i];
                        labels.push('<span class="', $scope.show_full_labels[key] ? 'label' : 'label-bar', ' label-', label.label, '">', $scope.show_full_labels[key] ? label.text : '', '</span>');
                        titles.push(label.text);
                    }
                }
                return ['<span title="', titles.join(', '), '" class="label-bars" style="overflow-x:scroll">', labels.join(''), '</span>'].join('');
            };


            // Build column defs for starting or ending labels
            const build_label_col_def = (labels_col, key) => {
                const header_cell_template = `<i ng-click="grid.appScope.toggle_labels('${labels_col}', '${key}')" class="ui-grid-cell-contents fas fa-chevron-circle-right" id="label-header-icon-${key}" style="margin:2px; float:right;"></i>`
                const cell_template = `<div ng-click="grid.appScope.toggle_labels(${labels_col}, '${key}')" class="ui-grid-cell-contents" ng-bind-html="grid.appScope.display_labels(row.entity, '${key}')"></div>`
                const width_fn = $scope.gridApi ? $scope.get_label_column_width(labels_col, key) : 30

                return {
                    name: labels_col,
                    displayName: '',
                    headerCellTemplate: header_cell_template,
                    cellTemplate: cell_template,
                    enableColumnMenu: false,
                    enableColumnMoving: false,
                    enableColumnResizing: false,
                    enableFiltering: false,
                    enableHiding: false,
                    enableSorting: false,
                    exporterSuppressExport: true,
                    // pinnedLeft: true,
                    visible: true,
                    width: width_fn,
                    maxWidth: $scope.max_label_width
                }
            }

            // ------------ DATA TABLE LOGIC ---------

            const set_site_eui_goal = (starting, ending, property) => {
                let site_eui = cycle_column_lookup.site_eui
                property.starting_site_eui = starting && starting[site_eui]
                property.starting_kbtu = Math.round(property.starting_sqft * property.starting_site_eui) || undefined
                property.ending_site_eui = ending && ending[site_eui]
                property.ending_kbtu = Math.round(property.ending_sqft * property.ending_site_eui) || undefined
                property.site_eui_change = percentage(property.starting_site_eui, property.ending_site_eui)
            }

            const format_properties = (properties) => {
                // properties = {cycle_id1: [properties1], cycle_id2: [properties2]}. 
                // there are some fields that span cycles (id, name, type)
                // and others are cycle specific (site EUI, sqft)

                let level = $scope.level_names[$scope.portfolioSummary.level_name_index]
                let ali = $scope.portfolioSummary.access_level_instance

                let starting_properties = properties[$scope.portfolioSummary.starting_cycle.id].filter(p => p[level] == ali)
                let ending_properties = properties[$scope.portfolioSummary.ending_cycle.id].filter(p => p[level] == ali)
                let flat_properties = [...starting_properties, ...ending_properties].flat()
                // labels are related to property views, but cross cycles displays based on property 
                // create a lookup between property_view.id to property.id
                $scope.property_lookup = {}
                flat_properties.forEach(p => $scope.property_lookup[p.property_view_id] = p.id)
                let unique_ids = [...new Set(flat_properties.map(property => property.id))]
                let gfa = cycle_column_lookup.gross_floor_area
                let combined_properties = []
                unique_ids.forEach(id => {
                    // find matching properties
                    let starting = starting_properties.find(p => p.id == id)
                    let ending = ending_properties.find(p => p.id == id)
                    // set accumulator
                    let property = starting || ending
                    // add starting stats
                    property.starting_cycle = $scope.portfolioSummary.starting_cycle.name
                    property.starting_sqft = starting && starting[gfa]
                    // add ending stats
                    property.ending_cycle = $scope.portfolioSummary.ending_cycle.name
                    property.ending_sqft = ending && ending[gfa]
                    // comparison stats
                    property.sqft_change = percentage(property.ending_sqft, property.starting_sqft)
                    // set_site_eui_goal(starting, ending, property)
                    $scope.goal_fn(starting, ending, property)

                    combined_properties.push(property)

                })
                return combined_properties
            }

            const apply_defaults = (cols, ...defaults) => { _.map(cols, (col) => _.defaults(col, ...defaults)) }

            const property_column_names = [...new Set(
                [
                    $scope.organization.property_display_field,
                    ...matching_column_names,
                    'property_name',
                    'property_type',
                ]
            )]
            // handle cycle specific columns
            const selected_columns = () => {
                let cols = property_column_names.map(name => $scope.columns.find(col => col.column_name === name))
                const default_starting = { headerCellClass: 'portfolio-summary-starting-header', cellClass: 'portfolio-summary-starting-cell' }
                const default_ending = { headerCellClass: 'portfolio-summary-ending-header', cellClass: 'portfolio-summary-ending-cell' }
                const default_styles = { headerCellFilter: 'translate', minWidth: 75, width: 150 }

                const starting_cols = [
                    { field: 'starting_cycle', displayName: 'Cycle' },
                    { field: 'starting_sqft', displayName: 'Sq. FT' },
                    { field: 'starting_site_eui', displayName: 'Site EUI' },
                    { field: 'starting_kbtu', displayName: 'kBTU' },
                    build_label_col_def('starting-labels', 'start')
                ]
                const ending_cols = [
                    { field: 'ending_cycle', displayName: 'Cycle' },
                    { field: 'ending_sqft', displayName: 'Sq. FT' },
                    { field: 'ending_site_eui', displayName: 'Site EUI' },
                    { field: 'ending_kbtu', displayName: 'kBTU' },
                    build_label_col_def('ending-labels', 'end')
                ]
                const summary_cols = [
                    { field: 'sqft_change', displayName: 'Sq Ft % Change' },
                    { field: 'site_eui_change', displayName: 'Site EUI % Improvement' },
                ]

                apply_defaults(starting_cols, default_starting)
                apply_defaults(ending_cols, default_ending)
                cols = [...cols, ...starting_cols, ...ending_cols, ...summary_cols]

                // Apply filters
                _.map(cols, (col) => {
                    let options = {};
                    // not an ideal solution. How is this done on the inventory list
                    if (col.column_name == 'pm_property_id') {
                        col.type = 'number'
                    }
                    if (col.data_type === 'datetime') {
                        options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
                        options.filter = inventory_service.dateFilter();
                    } else if (['area', 'eui', 'float', 'number'].includes(col.data_type)) {
                        options.cellFilter = 'number: ' + $scope.organization.display_decimal_places;
                        options.filter = inventory_service.combinedFilter();
                    } else {
                        options.filter = inventory_service.combinedFilter();
                    }
                    return _.defaults(col, options, default_styles);
                })

                add_access_level_names(cols)
                return cols

            }

            const add_access_level_names = (cols) => {
                $scope.organization.access_level_names.slice(1).reverse().forEach((level) => {
                    cols.unshift({
                        name: level,
                        displayName: level,
                        group: 'access_level_instance',
                        enableColumnMenu: true,
                        enableColumnMoving: false,
                        enableColumnResizing: true,
                        enableFiltering: true,
                        enableHiding: true,
                        enableSorting: true,
                        enablePinning: false,
                        exporterSuppressExport: true,
                        pinnedLeft: true,
                        visible: true,
                        width: 100,
                        cellClass: 'ali-cell',
                        headerCellClass: 'ali-header',
                    })
                })
            }

            $scope.show_access_level_instances = true
            $scope.toggle_access_level_instances = function () {
                $scope.show_access_level_instances = !$scope.show_access_level_instances
                $scope.gridOptions.columnDefs.forEach((col) => {
                    if (col.group == 'access_level_instance') {
                        col.visible = $scope.show_access_level_instances
                    }
                })
                $scope.gridApi.core.refresh();
            }

            const set_grid_options = (result) => {
                $scope.data = format_properties(result)
                $scope.gridOptions = {
                    data: 'data',
                    columnDefs: selected_columns($scope.columns),
                    enableFiltering: true,
                    enableHorizontalScrollbar: 1,
                    cellWidth: 200,
                    onRegisterApi: (gridApi) => {
                        $scope.gridApi = gridApi;
                    }
                }
            }

            // -------- SUMMARY LOGIC ------------

            const format_summary = () => {
                // summary consists of starting/ending total sqft, total kbtu, weigthed eui 
                // calc percentage for sqft change and eui improvment
                let starting_total_sqft = 0
                let starting_total_kbtu = 0
                let ending_total_sqft = 0
                let ending_total_kbtu = 0

                $scope.data.forEach(row => {
                    starting_total_sqft += row.starting_sqft || 0
                    starting_total_kbtu += row.starting_kbtu || 0
                    ending_total_sqft += row.ending_sqft || 0
                    ending_total_kbtu += row.ending_kbtu || 0
                })
                let starting_weighted_site_eui = Math.round(starting_total_kbtu / starting_total_sqft)
                let ending_weighted_site_eui = Math.round(ending_total_kbtu / ending_total_sqft)
                let sqft_change = percentage(ending_total_sqft, starting_total_sqft)
                let eui_change = percentage(starting_weighted_site_eui, ending_weighted_site_eui)

                return [{
                    starting_cycle: $scope.portfolioSummary.starting_cycle.name,
                    starting_total_sqft,
                    starting_total_kbtu,
                    starting_weighted_site_eui,
                    ending_cycle: $scope.portfolioSummary.ending_cycle.name,
                    ending_total_sqft,
                    ending_total_kbtu,
                    ending_weighted_site_eui,
                    sqft_change,
                    eui_change,
                }]
            }


            const summary_selected_columns = () => {
                const default_starting = { headerCellClass: 'portfolio-summary-starting-header', cellClass: 'portfolio-summary-starting-cell' }
                const default_ending = { headerCellClass: 'portfolio-summary-ending-header', cellClass: 'portfolio-summary-ending-cell' }
                const default_styles = { headerCellFilter: 'translate' }

                const starting_cols = [
                    { field: 'starting_cycle', displayName: 'Cycle' },
                    { field: 'starting_total_sqft', displayName: 'Total Sq. FT' },
                    { field: 'starting_total_kbtu', displayName: 'Total kBTU' },
                    { field: 'starting_weighted_site_eui', displayName: 'Site Eui' },
                ]
                const ending_cols = [
                    { field: 'ending_cycle', displayName: 'Cycle' },
                    { field: 'ending_total_sqft', displayName: 'Total Sq. FT' },
                    { field: 'ending_total_kbtu', displayName: 'Total kBTU' },
                    { field: 'ending_weighted_site_eui', displayName: 'Site Eui' },
                ]
                const calc_cols = [
                    { field: 'sqft_change', displayName: 'Sq. FT % Change' },
                    {
                        field: 'eui_change', displayName: 'EUI % Improvement', cellClass: (grid, row, col, rowRenderIndex, colRenderIndex) => {
                            return row.entity.eui_change >= $scope.portfolioSummary.goal ? 'above-target' : 'below-target'
                        }
                    },
                ]
                apply_defaults(starting_cols, default_starting, default_styles)
                apply_defaults(ending_cols, default_ending, default_styles)
                apply_defaults(calc_cols)

                return [...starting_cols, ...ending_cols, ...calc_cols]
            }

            const set_summary_grid_options = () => {
                $scope.summary_data = format_summary()
                $scope.summaryGridOptions = {
                    data: 'summary_data',
                    columnDefs: summary_selected_columns()
                }
            }

        }
    ]
)