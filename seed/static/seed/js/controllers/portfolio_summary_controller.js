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
            uiGridConstants,
            gridUtil,
        ) {
            $scope.cycles = cycles.cycles;
            $scope.columns = property_columns;
            $scope.goal_columns = [$scope.columns.find(c => c.column_name == 'source_eui')]
            const matching_column_names = $scope.columns.filter(col => col.is_matching_criteria).map(col => col.column_name)
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
                console.log($scope.potential_level_instances)
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
                goal_column: 'source_eui',
                goal: 0,
                baseline_cycle: $scope.cycles.find(c => c.id == 3),
                current_cycle: $scope.cycles.find(c => c.id == 2),
                // level_name_index
                // access_level_instance
            };


            $scope.refresh_data = () => {
                $scope.data_valid = false;
                $scope.summary_valid= false;
                console.log('refresh_data')
                expected_keys = ['baseline_cycle', 'current_cycle', 'goal', 'goal_column', 'level_name_index', 'access_level_instance']
                valid = expected_keys.every(key => key in $scope.portfolioSummary);
                if (!valid) {
                    console.log('not valid')
                    return
                }
                $scope.data_loading = true;
                $scope.summary_loading = true;
                console.log($scope.portfolioSummary)
                const cycle_ids = [$scope.portfolioSummary.baseline_cycle.id, $scope.portfolioSummary.current_cycle.id]
                inventory_service.get_portfolio_summary(cycle_ids[0]).then(result => {
                    summary = result.data.data ;
                    console.log('got summary data')
                    set_summary_grid_options(summary);
                }).then(() => {
                    $scope.summary_loading = false;
                    $scope.summary_valid = true;
                })
                inventory_service.properties_cycle(undefined, cycle_ids).then(result => {
                    console.log('got data')
                    get_all_labels();
                    set_grid_options(result);
                }).then(() => { 
                    $scope.data_valid = true;
                    $scope.data_loading = false;
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
            $scope.show_full_labels = { baseline: false, current: false }
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
                get_labels('baseline');
                get_labels('current');
            }
            const get_labels = (key) => {
                const cycle = key == 'baseline' ? $scope.portfolioSummary.baseline_cycle : $scope.portfolioSummary.current_cycle;

                label_service.get_labels('properties', undefined, cycle.id).then((current_labels) => {                    
                    let labels = _.filter(current_labels, (label) => !_.isEmpty(label.is_applied));

                    // load saved label filter
                    const ids = inventory_service.loadSelectedLabels(localStorageLabelKey);
                    // $scope.selected_labels = _.filter(labels, (label) => _.includes(ids, label.id));
                    
                    if (key == 'baseline') {
                        $scope.baseline_labels = labels
                        $scope.build_labels(key, $scope.baseline_labels);
                    } else {
                        $scope.current_labels = labels
                        $scope.build_labels(key, $scope.current_labels);
                    }
                });
            };

            // Find labels that should be displayed and organize by applied inventory id
            $scope.show_labels_by_inventory_id = {baseline: {}, current: {}};
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


            // Build column defs for baseline or current labels
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

            const set_site_eui_goal = (baseline, current, property) => {
                let site_eui = cycle_column_lookup.site_eui
                property.baseline_site_eui = baseline && baseline[site_eui]
                property.baseline_kbtu = Math.round(property.baseline_sqft * property.baseline_site_eui) || undefined
                property.current_site_eui = current && current[site_eui]
                property.current_kbtu = Math.round(property.current_sqft * property.current_site_eui) || undefined
                property.site_eui_change = percentage(property.baseline_site_eui, property.current_site_eui)
            }

            const format_properties = (properties) => {
                // properties = {cycle_id1: [properties1], cycle_id2: [properties2]}. 
                // there are some fields that span cycles (id, name, type)
                // and others are cycle specific (site EUI, sqft)

                let level = $scope.level_names[$scope.portfolioSummary.level_name_index]
                let ali_id = $scope.portfolioSummary.access_level_instance
                let ali_name = $scope.potential_level_instances.find(ali => ali.id == ali_id).name

                let baseline_properties = properties[$scope.portfolioSummary.baseline_cycle.id].filter(p => p[level] == ali_name)
                let current_properties = properties[$scope.portfolioSummary.current_cycle.id].filter(p => p[level] == ali_name)
                let flat_properties = [...baseline_properties, ...current_properties].flat()
                // labels are related to property views, but cross cycles displays based on property 
                // create a lookup between property_view.id to property.id
                $scope.property_lookup = {}
                flat_properties.forEach(p => $scope.property_lookup[p.property_view_id] = p.id)
                let unique_ids = [...new Set(flat_properties.map(property => property.id))]
                let gfa = cycle_column_lookup.gross_floor_area
                let combined_properties = []
                unique_ids.forEach(id => {
                    // find matching properties
                    let baseline = baseline_properties.find(p => p.id == id)
                    let current = current_properties.find(p => p.id == id)
                    // set accumulator
                    let property = baseline || current
                    // add baseline stats
                    property.baseline_cycle = $scope.portfolioSummary.baseline_cycle.name
                    property.baseline_sqft = baseline && baseline[gfa]
                    // add current stats
                    property.current_cycle = $scope.portfolioSummary.current_cycle.name
                    property.current_sqft = current && current[gfa]
                    // comparison stats
                    property.sqft_change = percentage(property.current_sqft, property.baseline_sqft)
                    // set_site_eui_goal(baseline, current, property)
                    set_site_eui_goal(baseline, current, property)

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
                const default_baseline = { headerCellClass: 'portfolio-summary-baseline-header', cellClass: 'portfolio-summary-baseline-cell' }
                const default_current = { headerCellClass: 'portfolio-summary-current-header', cellClass: 'portfolio-summary-current-cell' }
                const default_styles = { headerCellFilter: 'translate', minWidth: 75, width: 150 }

                const baseline_cols = [
                    { field: 'baseline_cycle', displayName: 'Cycle' },
                    { field: 'baseline_sqft', displayName: 'Sq. FT' },
                    { field: 'baseline_site_eui', displayName: 'Site EUI' },
                    { field: 'baseline_kbtu', displayName: 'kBTU' },
                    build_label_col_def('baseline-labels', 'baseline')
                ]
                const current_cols = [
                    { field: 'current_cycle', displayName: 'Cycle' },
                    { field: 'current_sqft', displayName: 'Sq. FT' },
                    { field: 'current_site_eui', displayName: 'Site EUI' },
                    { field: 'current_kbtu', displayName: 'kBTU' },
                    build_label_col_def('current-labels', 'current')
                ]
                const summary_cols = [
                    { field: 'sqft_change', displayName: 'Sq Ft % Change' },
                    { field: 'site_eui_change', displayName: 'Site EUI % Improvement' },
                ]

                apply_defaults(baseline_cols, default_baseline)
                apply_defaults(current_cols, default_current)
                cols = [...cols, ...baseline_cols, ...current_cols, ...summary_cols]

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

            const summary_selected_columns = () => {
                const default_baseline = { headerCellClass: 'portfolio-summary-baseline-header', cellClass: 'portfolio-summary-baseline-cell' }
                const default_current = { headerCellClass: 'portfolio-summary-current-header', cellClass: 'portfolio-summary-current-cell' }
                const default_styles = { headerCellFilter: 'translate' }

                const baseline_cols = [
                    { field: 'baseline_cycle', displayName: 'Cycle' },
                    { field: 'baseline_total_sqft', displayName: 'Total Sq. FT' },
                    { field: 'baseline_total_kbtu', displayName: 'Total kBTU' },
                    { field: 'baseline_weighted_site_eui', displayName: 'Site Eui' },
                ]
                const current_cols = [
                    { field: 'current_cycle', displayName: 'Cycle' },
                    { field: 'current_total_sqft', displayName: 'Total Sq. FT' },
                    { field: 'current_total_kbtu', displayName: 'Total kBTU' },
                    { field: 'current_weighted_site_eui', displayName: 'Site Eui' },
                ]
                const calc_cols = [
                    { field: 'sqft_change', displayName: 'Sq. FT % Change' },
                    {
                        field: 'eui_change', displayName: 'EUI % Improvement', cellClass: (grid, row, col, rowRenderIndex, colRenderIndex) => {
                            return row.entity.eui_change >= $scope.portfolioSummary.goal ? 'above-target' : 'below-target'
                        }
                    },
                ]
                apply_defaults(baseline_cols, default_baseline, default_styles)
                apply_defaults(current_cols, default_current, default_styles)
                apply_defaults(calc_cols)

                return [...baseline_cols, ...current_cols, ...calc_cols]
            }

            const format_summary = (summary) => {
                const baseline = summary.baseline
                const current = summary.current
                return [{
                    baseline_cycle: baseline.cycle_name,
                    baseline_total_sqft: baseline.total_sqft,
                    baseline_total_kbtu: baseline.total_kbtu,
                    baseline_weighted_site_eui: baseline.weighted_eui,
                    current_cycle: current.cycle_name,
                    current_total_sqft: current.total_sqft,
                    current_total_kbtu: current.total_kbtu,
                    current_weighted_site_eui: current.weighted_eui,
                    sqft_change: summary.sqft_change,
                    eui_change: summary.eui_change,
                }]
            }

            const set_summary_grid_options = (summary) => {
                $scope.summary_data = format_summary(summary)
                console.log($scope.summary_data)
                $scope.summaryGridOptions = {
                    data: 'summary_data',
                    columnDefs: summary_selected_columns()
                }
            }

        }
    ]
)