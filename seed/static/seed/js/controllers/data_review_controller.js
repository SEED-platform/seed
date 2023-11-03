/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.data_review', [])
    .controller('data_review_controller', [
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
                new_level_instance_depth = parseInt($scope.dataReview.level_name_index) + 1
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth]
            }

            const cycle_column_keys = ['gross_floor_area', 'site_eui',]
            const cycle_column_vals = property_columns.filter(c => cycle_column_keys.includes(c.column_name)).map(c => c.name)
            // convert column_name to name
            const cycle_column_lookup = Object.fromEntries(_.zip(cycle_column_keys, cycle_column_vals))

            const site_eui_column = property_columns.find(col => col.column_name == 'site_eui');
            $scope.dataReview = {
                goal_column: site_eui_column.id,
                goal: 0,
                // temp
                starting_cycle: $scope.cycles.find(c => c.id == 3),
                ending_cycle: $scope.cycles.find(c => c.id == 4),
                // level_name_index
                // access_level_instance
            };


            $scope.refresh_data = () => {
                console.log('refresh_data')
                expected_keys = ['starting_cycle', 'ending_cycle', 'goal', 'goal_column', 'level_name_index', 'access_level_instance']
                valid = expected_keys.every(key => key in $scope.dataReview)
                if (!valid) {
                    console.log('not valid')
                    return
                }
                console.log($scope.dataReview)
                spinner_utility.show()
                const cycle_ids = [$scope.dataReview.starting_cycle.id, $scope.dataReview.ending_cycle.id]
                
                inventory_service.properties_cycle(undefined, cycle_ids).then(result => {
                    $scope.data = format_properties(result)
                    $scope.summary_data = format_summary()
                    get_all_labels()
                    set_grid_options()
                    // $scope.updateHeight()
                }).then(() => { 
                    $scope.valid = true;
                    spinner_utility.hide() 
                })
            }
            $scope.refresh_data()

            const format_properties = (properties) => {
                // properties = {cycle_id1: [properties1], cycle_id2: [properties2]}. 
                // there are some fields that span cycles (id, name, type)
                // and others are cycle specific (site EUI, sqft)

                let level = $scope.level_names[$scope.dataReview.level_name_index]
                let ali = $scope.dataReview.access_level_instance

                let starting_properties = properties[$scope.dataReview.starting_cycle.id].filter(p => p[level] == ali)
                let ending_properties = properties[$scope.dataReview.ending_cycle.id].filter(p => p[level] == ali)
                let flat_properties = [...starting_properties, ...ending_properties].flat()
                // labels are related to property views, but cross cycles displays based on property 
                // create a lookup between property_view.id to property.id
                $scope.property_lookup = {}
                flat_properties.forEach(p => $scope.property_lookup[p.property_view_id] = p.id)
                let unique_ids = [...new Set(flat_properties.map(property => property.id))]
                let site_eui = cycle_column_lookup.site_eui
                let gfa = cycle_column_lookup.gross_floor_area
                let combined_properties = []
                unique_ids.forEach(id => {
                    // find matching properties
                    let starting = starting_properties.find(p => p.id == id)
                    let ending = ending_properties.find(p => p.id == id)
                    // set accumulator
                    let property = starting || ending

                    // add starting stats
                    property.starting_period = $scope.dataReview.starting_cycle.end
                    property.starting_sqft = starting && starting[gfa]
                    property.starting_site_eui = starting && starting[site_eui]
                    property.starting_kbtu = Math.round(property.starting_sqft * property.starting_site_eui) || undefined
                    // add ending stats
                    property.ending_period = $scope.dataReview.ending_cycle.end
                    property.ending_sqft = ending && ending[gfa]
                    property.ending_site_eui = ending && ending[site_eui]
                    property.ending_kbtu = Math.round(property.ending_sqft * property.ending_site_eui) || undefined
                    // comparison stats
                    property.sqft_change = percentage(property.ending_sqft, property.starting_sqft)
                    property.site_eui_change = percentage(property.starting_site_eui, property.ending_site_eui)

                    combined_properties.push(property)

                })
                return combined_properties
            }


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
                    starting_period: $scope.dataReview.starting_cycle.end,
                    starting_total_sqft,
                    starting_total_kbtu,
                    starting_weighted_site_eui,
                    ending_period: $scope.dataReview.ending_cycle.end,
                    ending_total_sqft,
                    ending_total_kbtu,
                    ending_weighted_site_eui,
                    sqft_change,
                    eui_change,
                }]
            }

            const percentage = (a, b) => {
                return Math.round((a - b) / a * 100)
            }

            // LABEL LOGIC START
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
                    const icon = document.getElementById('label-header-icon');
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
                const cycle = key == 'start' ? $scope.dataReview.starting_cycle : $scope.dataReview.ending_cycle;

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
                const header_cell_template = `<i ng-click="grid.appScope.toggle_labels('${labels_col}', '${key}')" class="ui-grid-cell-contents fas fa-chevron-circle-right" id="label-header-icon" style="margin:2px; float:right;"></i>`
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

            // LABEL LOGIC END
            const apply_defaults = (cols, ...defaults) => { _.map(cols, (col) => _.defaults(col, ...defaults)) }

            const property_column_names = [
                'pm_property_id',
                'property_name',
                'property_type',
                'postal_code',
            ]
            // handle cycle specific columns
            const selected_columns = () => {
                let cols = $scope.columns.filter(col => property_column_names.includes(col.column_name))
                const default_starting = { headerCellClass: 'data-review-starting-header', cellClass: 'data-review-starting-cell' }
                const default_ending = { headerCellClass: 'data-review-ending-header', cellClass: 'data-review-ending-cell' }
                const default_styles = { headerCellFilter: 'translate', minWidth: 75, width: 150 }

                cols.forEach(col => col.parentColumn = 'parent')
                const starting_cols = [
                    { field: 'starting_period', displayName: 'Period' },
                    { field: 'starting_sqft', displayName: 'Sq. FT' },
                    { field: 'starting_site_eui', displayName: 'Site EUI' },
                    { field: 'starting_kbtu', displayName: 'kBTU' },
                    build_label_col_def('starting-labels', 'start')
                ]
                const ending_cols = [
                    { field: 'ending_period', displayName: 'Period' },
                    { field: 'ending_sqft', displayName: 'Sq. FT' },
                    { field: 'ending_site_eui', displayName: 'Site EUI' },
                    { field: 'ending_kbtu', displayName: 'kBTU' },
                    build_label_col_def('ending-labels', 'end')
                ]
                const summary_cols = [
                    { field: 'site_eui_change', displayName: 'Site EUI % Improvement' },
                    { field: 'sqft_change', displayName: 'Sq Ft % Change' },
                ]

                apply_defaults(starting_cols, default_starting)
                apply_defaults(ending_cols, default_ending)
                cols = [...cols, ...starting_cols, ...ending_cols, ...summary_cols]

                // Apply filters
                _.map(cols, (col) => {
                    let options = {};
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
                $scope.organization.access_level_names.reverse().slice(0, -1).forEach((level) => {
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

            const set_grid_options = () => {
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

            const summary_selected_columns = () => {
                const default_starting = { headerCellClass: 'data-review-starting-header', cellClass: 'data-review-starting-cell' }
                const default_ending = { headerCellClass: 'data-review-ending-header', cellClass: 'data-review-ending-cell' }
                const default_styles = { headerCellFilter: 'translate' }

                const starting_cols = [
                    { field: 'starting_period', displayName: 'Period (Start)' },
                    { field: 'starting_total_sqft', displayName: 'Total Sq. FT (Start)' },
                    { field: 'starting_total_kbtu', displayName: 'Total kBTU (Start)' },
                    { field: 'starting_weighted_site_eui', displayName: 'Site Eui (Start)' },
                ]
                const ending_cols = [
                    { field: 'ending_period', displayName: 'Period (End)' },
                    { field: 'ending_total_sqft', displayName: 'Total Sq. FT (End)' },
                    { field: 'ending_total_kbtu', displayName: 'Total kBTU (End)' },
                    { field: 'ending_weighted_site_eui', displayName: 'Site Eui (End)' },
                ]
                const calc_cols = [
                    { field: 'sqft_change', displayName: 'Sq. FT % Change' },
                    {
                        field: 'eui_change', displayName: 'EUI % Improvement', cellClass: (grid, row, col, rowRenderIndex, colRenderIndex) => {
                            return row.entity.eui_change >= $scope.dataReview.goal ? 'above-target' : 'below-target'
                        }
                    },
                ]
                apply_defaults(starting_cols, default_starting, default_styles)
                apply_defaults(ending_cols, default_ending, default_styles)
                apply_defaults(calc_cols)

                return [...starting_cols, ...ending_cols, ...calc_cols]
            }

            $scope.summaryGridOptions = {
                data: 'summary_data',
                columnDefs: summary_selected_columns()
            }

        }
    ]
)