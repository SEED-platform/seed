/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.portfolio_summary', [])
    .controller('portfolio_summary_controller', [
        '$scope',
        '$state',
        '$stateParams',
        '$uibModal',
        'urls',
        'inventory_service',
        'label_service',
        'goal_service',
        'cycles',
        'organization_payload',
        'access_level_tree',
        'property_columns',
        'uiGridConstants',
        'gridUtil',
        'spinner_utility',
        function (
            $scope,
            $state,
            $stateParams,
            $uibModal,
            urls,
            inventory_service,
            label_service,
            goal_service,
            cycles,
            organization_payload,
            access_level_tree,
            property_columns,
            uiGridConstants,
            gridUtil,
            spinner_utility,
        ) {
            $scope.organization = organization_payload.organization;
            // Ii there a better way to convert string units to displayUnits?
            const area_units = $scope.organization.display_units_area.replace('**2', '²');
            const eui_units = $scope.organization.display_units_eui.replace('**2', '²');
            $scope.cycles = cycles.cycles;
            $scope.access_level_tree = access_level_tree.access_level_tree;
            $scope.level_names = access_level_tree.access_level_names;
            const localStorageLabelKey = `grid.properties.labels`;
            $scope.goal = {};
            $scope.columns = property_columns;
            $scope.cycle_columns = [];
            $scope.area_columns = [];
            $scope.eui_columns = [];
            let matching_column_names = [];
            let table_column_ids = [];

            const initialize_columns = () => {
                $scope.columns.forEach(c => {
                    const default_display = c.column_name == $scope.organization.property_display_field;
                    const matching = c.is_matching_criteria;
                    const area = c.data_type === 'area';
                    const eui = c.data_type === 'eui';
                    const other = ['property_name', 'property_type'].includes(c.column_name);

                    if (default_display || matching || eui || area || other ) table_column_ids.push(c.id);
                    if (eui) $scope.eui_columns.push(c);
                    if (area) $scope.area_columns.push(c);
                    if (matching) matching_column_names.push(c.column_name);
                })
            }
            initialize_columns()

            // Can only sort based on baseline or current, not both. In the event of a conflict, use the more recent.
            baseline_first = false

            // optionally pass a goal name to be set as $scope.goal - used on modal close
            const get_goals = (goal_name=false) => {
                goal_service.get_goals().then(result => {
                    $scope.goals = _.isEmpty(result.goals) ? [] : result.goals
                    $scope.goal = goal_name ?
                        $scope.goals.find(goal => goal.name == goal_name) :
                        $scope.goals[0]
                })
            }
            get_goals()

            // If goal changes, reset grid filters and repopulate ui-grids
            $scope.$watch('goal', () => {
                if ($scope.gridApi) $scope.reset_sorts_filters();
                $scope.data_valid = false;
                if (_.isEmpty($scope.goal)) {
                    $scope.valid = false;
                    $scope.summary_valid = false;
                } else {
                    reset_data();
                }
            })

            const reset_data = () => {
                $scope.valid = true;
                format_goal_details();
                $scope.refresh_data();
            }

            // selected goal details
            const format_goal_details = () => {
                $scope.change_selected_level_index()
                const get_column_name = (column_id) => $scope.columns.find(c => c.id == column_id).displayName
                const get_cycle_name = (cycle_id) => $scope.cycles.find(c => c.id == cycle_id).name
                const level_name = $scope.level_names[$scope.goal.level_name_index]
                const access_level_instance = $scope.potential_level_instances.find(level => level.id == $scope.goal.access_level_instance).name

                $scope.goal_details = [
                    ['Baseline Cycle', get_cycle_name($scope.goal.baseline_cycle)],
                    ['Current Cycle', get_cycle_name($scope.goal.current_cycle)],
                    [level_name, access_level_instance],
                    ['Portfolio Target', `${$scope.goal.target_percentage} %`],
                    ['Area Column', get_column_name($scope.goal.area_column)],
                    ['Primary Column', get_column_name($scope.goal.eui_column1)],
                ]
                if ($scope.goal.eui_column2) {
                    $scope.goal_details.push(['Secondary Column', get_column_name($scope.goal.eui_column2)])
                }
                if ($scope.goal.eui_column3) {
                    $scope.goal_details.push(['Tertiary Column', get_column_name($scope.goal.eui_column3)])
                }
            }

            // from inventory_list_controller
            $scope.columnDisplayByName = {};
            for (const i in $scope.columns) {
                $scope.columnDisplayByName[$scope.columns[i].name] = $scope.columns[i].displayName;
            }

            // Build out access_level_instances_by_depth recurrsively
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
                new_level_instance_depth = parseInt($scope.goal.level_name_index) + 1
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth]
            }

            // GOAL EDITOR MODAL
            $scope.open_goal_editor_modal = () => {
                const modalInstance = $uibModal.open({
                    templateUrl: `${urls.static_url}seed/partials/goal_editor_modal.html`,
                    controller: 'goal_editor_modal_controller',
                    size: 'lg',
                    backdrop: 'static',
                    resolve: {
                        organization: () => $scope.organization,
                        cycles: () => $scope.cycles,
                        area_columns: () => $scope.area_columns,
                        eui_columns: () => $scope.eui_columns,
                        access_level_tree: () => access_level_tree,
                        goal: () => $scope.goal,
                    },
                });

                // on modal close
                modalInstance.result.then((goal_name) => {
                    get_goals(goal_name)
                })
            }

            $scope.refresh_data = () => {
                $scope.summary_loading = true;
                load_summary();
                $scope.load_inventory(1);
            }

            const load_summary = () => {
                $scope.show_access_level_instances = true;
                $scope.summary_valid = false;

                goal_service.get_portfolio_summary($scope.goal.id).then(result => {
                    summary = result.data;
                    set_summary_grid_options(summary);
                }).then(() => {
                    $scope.summary_loading = false;
                    $scope.summary_valid = true;
                })
            }

            $scope.page_change = (page) => {
                spinner_utility.show()
                $scope.load_inventory(page)
            }
            $scope.load_inventory = (page) => {
                $scope.data_loading = true;

                let access_level_instance_id = $scope.goal.access_level_instance
                let combined_result = {}
                let per_page = 50
                let current_cycle = {id: $scope.goal.current_cycle}
                let baseline_cycle = {id: $scope.goal.baseline_cycle}
                // order of cycle property filter is dynamic based on column_sorts
                let cycle_priority = baseline_first ? [baseline_cycle, current_cycle]: [current_cycle, baseline_cycle]

                get_paginated_properties(page, per_page, cycle_priority[0], access_level_instance_id, true).then(result0 => {
                    $scope.inventory_pagination = result0.pagination
                    properties = result0.results
                    combined_result[cycle_priority[0].id] = properties;
                    property_ids = properties.map(p => p.id)

                    get_paginated_properties(page, per_page, cycle_priority[1], access_level_instance_id, false, property_ids).then(result1 => {
                        properties = result1.results
                        combined_result[cycle_priority[1].id] = properties;
                        get_all_labels()
                        set_grid_options(combined_result)

                    }).then(() => {
                        $scope.data_loading = false;
                        $scope.data_valid = true
                    })
                })
            }

            const get_paginated_properties = (page, chunk, cycle, access_level_instance_id, include_filters_sorts, include_property_ids=null) => {
                fn = inventory_service.get_properties;
                const [filters, sorts] = include_filters_sorts ? [$scope.column_filters, $scope.column_sorts] : [[],[]]

                return fn(
                    page,
                    chunk,
                    cycle,
                    undefined,  // profile_id
                    undefined,  // include_view_ids
                    undefined,  // exclude_view_ids
                    true,  // save_last_cycle
                    $scope.organization.id,
                    true,  // include_related
                    filters,
                    sorts,
                    false,  // ids_only
                    table_column_ids.join(),
                    access_level_instance_id,
                    include_property_ids,
                );
            };

            const percentage = (a, b) => {
                if (!a) return null;
                const value = Math.round((a - b) / a * 100);
                return isNaN(value) ? null : value;
            }

            // -------------- LABEL LOGIC -------------

            $scope.max_label_width = 750;
            $scope.get_label_column_width = (labels_col, key) => {
                if (!$scope.show_full_labels[key]) {
                    return 30;
                }
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
                const cycle = key == 'baseline' ? $scope.goal.baseline_cycle : $scope.goal.current_cycle;

                label_service.get_labels('properties', undefined, cycle).then((current_labels) => {
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
                const cell_template = `<div ng-click="grid.appScope.toggle_labels('${labels_col}', '${key}')" class="ui-grid-cell-contents" ng-bind-html="grid.appScope.display_labels(row.entity, '${key}')"></div>`
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

            const set_eui_goal = (baseline, current, property, preferred_columns) => {
                // only check defined columns
                for (let col of preferred_columns.filter(c => c)) {
                    if (baseline && property.baseline_eui == undefined) {
                        property.baseline_eui = baseline[col.name]
                    }
                    if (current && property.current_eui == undefined) {
                        property.current_eui = current[col.name]
                    }
                }

                property.baseline_kbtu = Math.round(property.baseline_sqft * property.baseline_eui) || undefined
                property.current_kbtu = Math.round(property.current_sqft * property.current_eui) || undefined
                property.eui_change = percentage(property.baseline_eui, property.current_eui)
            }

            const format_properties = (properties) => {
                const area = $scope.columns.find(c => c.id == $scope.goal.area_column)
                const preferred_columns = [$scope.columns.find(c => c.id == $scope.goal.eui_column1)]
                if ($scope.goal.eui_column2) preferred_columns.push($scope.columns.find(c => c.id == $scope.goal.eui_column2))
                if ($scope.goal.eui_column3) preferred_columns.push($scope.columns.find(c => c.id == $scope.goal.eui_column3))

                const baseline_cycle_name = $scope.cycles.find(c => c.id == $scope.goal.baseline_cycle).name
                const current_cycle_name = $scope.cycles.find(c => c.id == $scope.goal.current_cycle).name
                // some fields span cycles (id, name, type)
                // and others are cycle specific (source EUI, sqft)
                let current_properties = properties[$scope.goal.current_cycle]
                let baseline_properties = properties[$scope.goal.baseline_cycle]
                let flat_properties = baseline_first ?
                    [baseline_properties, current_properties].flat() :
                    [current_properties, baseline_properties].flat()

                // labels are related to property views, but cross cycles displays based on property
                // create a lookup between property_view.id to property.id
                $scope.property_lookup = {}
                flat_properties.forEach(p => $scope.property_lookup[p.property_view_id] = p.id)
                let unique_ids = [...new Set(flat_properties.map(property => property.id))]
                let combined_properties = []
                unique_ids.forEach(id => {
                    // find matching properties
                    let baseline = baseline_properties.find(p => p.id == id)
                    let current = current_properties.find(p => p.id == id)
                    // set accumulator
                    let property = current || baseline
                    // add baseline stats
                    if (baseline) {
                        property.baseline_cycle = baseline_cycle_name
                        property.baseline_sqft = baseline[area.name]
                    }
                    // add current stats
                    if (current) {
                        property.current_cycle = current_cycle_name
                        property.current_sqft = current[area.name]
                    }
                    // comparison stats
                    property.sqft_change = percentage(property.current_sqft, property.baseline_sqft)
                    set_eui_goal(baseline, current, property, preferred_columns)
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
                    { field: 'baseline_cycle', displayName: 'Cycle'},
                    { field: 'baseline_sqft', displayName: `Area (${area_units})`, cellFilter: 'number'},
                    { field: 'baseline_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number'},
                    // ktbu acts as a derived column. Disable sorting filtering
                    {
                        field: 'baseline_kbtu', displayName: 'kBTU', cellFilter: 'number',
                        enableFiltering: false, enableSorting: false,
                        headerCellClass: 'derived-column-display-name portfolio-summary-baseline-header'
                    },
                    build_label_col_def('baseline-labels', 'baseline')
                ]
                const current_cols = [
                    { field: 'current_cycle', displayName: 'Cycle'},
                    { field: 'current_sqft', displayName: `Area (${area_units})`, cellFilter: 'number'},
                    { field: 'current_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number'},
                    {
                        field: 'current_kbtu', displayName: 'kBTU', cellFilter: 'number',
                        enableFiltering: false, enableSorting: false,
                        headerCellClass: 'derived-column-display-name portfolio-summary-current-header'
                    },
                    build_label_col_def('current-labels', 'current')
                ]
                const summary_cols = [
                    { field: 'sqft_change', displayName: 'Sq Ft % Change', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name' },
                    { field: 'eui_change', displayName: 'EUI % Improvement', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name' },
                ]

                apply_defaults(baseline_cols, default_baseline)
                apply_defaults(current_cols, default_current)
                cols = [...cols, ...baseline_cols, ...current_cols, ...summary_cols]

                // Apply filters
                // from inventory_list_controller
                _.map(cols, (col) => {
                    let options = {};
                    if (col.pinnedLeft) {
                        col.pinnedLeft = false;
                    }
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

                apply_cycle_sorts_and_filters(cols)
                add_access_level_names(cols)
                return cols

            }

            const apply_cycle_sorts_and_filters = (columns) => {
                // Cycle specific columns filters and sorts must be set manually
                const cycle_columns = ['baseline_cycle', 'baseline_sqft', 'baseline_eui', 'baseline_kbtu', 'current_cycle', 'current_sqft', 'current_eui', 'current_kbtu', 'sqft_change', 'eui_change']

                columns.forEach(column => {
                    if (cycle_columns.includes(column.field)) {
                        let cycle_column = $scope.cycle_columns.find(c => c.name == column.field)
                        column.sort = cycle_column ? cycle_column.sort : {}
                        column.filter.term = cycle_column ? cycle_column.filters[0].term : null
                    }
                })
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

            $scope.toggle_access_level_instances = function () {
                $scope.show_access_level_instances = !$scope.show_access_level_instances
                $scope.gridOptions.columnDefs.forEach((col) => {
                    if (col.group == 'access_level_instance') {
                        col.visible = $scope.show_access_level_instances
                    }
                })
                $scope.gridApi.core.refresh();
            }

            const format_cycle_columns = (columns) => {
                /* filtering is based on existing db columns.
                ** The PortfilioSummary uses cycle specific columns that do not exist elsewhere ('baseline_eui', 'current_sqft')
                ** To sort on these columns, override the column name to the cannonical column, and set the cycle filter order
                ** ex: if sort = {name: 'baseline_sqft'}, set {name: 'gross_floor_area_##'} and filter for baseline properties frist.

                ** NOTE:
                ** cant fitler on cycle - cycle is not a column
                ** cant filter on kbtu, sqft_change, eui_change - not real columns. calc'ed from eui and sqft. (similar to derived columns)
                */
                let eui_column = $scope.columns.find(c => c.id == $scope.goal.eui_column1)
                let area_column = $scope.columns.find(c => c.id == $scope.goal.area_column)

                const cycle_column_lookup = {
                    'baseline_eui': eui_column.name,
                    'baseline_sqft': area_column.name,
                    'current_eui': eui_column.name,
                    'current_sqft': area_column.name,
                }
                $scope.cycle_columns = []

                columns.forEach(column => {
                    if (cycle_column_lookup[column.name]) {
                        $scope.cycle_columns.push({...column})
                        column.name = cycle_column_lookup[column.name]
                    }
                })

                return columns

            }

            const remove_conflict_columns = (grid_columns) => {
                // Property's are returned from 2 different get requests. One for the current, one for the baseline
                // The second filter is solely based on the property ids from the first
                // Filtering on the first and  second will result in unrepresntative data
                // Remove the conflict to allow sorting/filtering on either baseline or current.

                const column_names = grid_columns.map(c => c.name);
                const includes_baseline = column_names.some(name => name.includes('baseline'));
                const includes_current = column_names.some(name => name.includes('current'));
                const conflict = includes_baseline && includes_current;

                if (conflict) {
                    baseline_first = !baseline_first;
                    const excluded_name = baseline_first ? 'current' : 'baseline';
                    grid_columns = grid_columns.filter(column => !column.name.includes(excluded_name));
                } else if (includes_baseline) {
                    baseline_first = true;
                } else if (includes_current) {
                    baseline_first = false;
                }

                return grid_columns
            }


            // from inventory_list_controller
            const updateColumnFilterSort = () => {
                let grid_columns = _.filter($scope.gridApi.saveState.save().columns, (col) => _.keys(col.sort).filter((key) => key !== 'ignoreSort').length + (_.get(col, 'filters[0].term', '') || '').length > 0);
                // check filter/sort columns. Cannot filter on both baseline and current. choose the more recent filter/sort
                grid_columns = remove_conflict_columns(grid_columns)
                // convert cycle columnss to cannonical columns
                let formatted_columns = format_cycle_columns(grid_columns)

                // inventory_service.saveGridSettings(`${localStorageKey}.sort`, {
                //     columns
                // });
                $scope.column_filters = [];
                // parse the filters and sorts
                for (let column of formatted_columns) {
                    // format column if cycle specific
                    const { name, filters, sort } = column;
                    // remove the column id at the end of the name
                    const column_name = name.split('_').slice(0, -1).join('_');

                    for (const filter of filters) {
                        if (_.isEmpty(filter)) {
                            continue;
                        }

                        // a filter can contain many comma-separated filters
                        const subFilters = _.map(_.split(filter.term, ','), _.trim);
                        for (const subFilter of subFilters) {
                            if (subFilter) {
                                const { string, operator, value } = parseFilter(subFilter);
                                const index = $scope.columns.findIndex((p) => p.name === column_name);
                                const display = [$scope.columnDisplayByName[name], string, value].join(' ');
                                $scope.column_filters.push({
                                    name,
                                    column_name,
                                    operator,
                                    value,
                                    display
                                });
                            }
                        }
                    }

                    if (sort.direction) {
                        // remove the column id at the end of the name
                        const column_name = name.split('_').slice(0, -1).join('_');
                        const display = [$scope.columnDisplayByName[name], sort.direction].join(' ');
                        $scope.column_sorts = [{
                            name,
                            column_name,
                            direction: sort.direction,
                            display,
                            priority: sort.priority
                        }];
                        // $scope.column_sorts.sort((a, b) => a.priority > b.priority);
                    }
                }
                // $scope.isModified();
            };

            // from inventory_list_controller
            // https://regexr.com/6cka2
            const combinedRegex = /^(!?)=\s*(-?\d+(?:\.\d+)?)$|^(!?)=?\s*"((?:[^"]|\\")*)"$|^(<=?|>=?)\s*((-?\d+(?:\.\d+)?)|(\d{4}-\d{2}-\d{2}))$/;
            const parseFilter = (expression) => {
                // parses an expression string into an object containing operator and value
                const filterData = expression.match(combinedRegex);
                if (filterData) {
                    if (!_.isUndefined(filterData[2])) {
                        // Numeric Equality
                        const operator = filterData[1];
                        const value = Number(filterData[2].replace('\\.', '.'));
                        if (operator === '!') {
                            return { string: 'is not', operator: 'ne', value };
                        }
                        return { string: 'is', operator: 'exact', value };
                    }
                    if (!_.isUndefined(filterData[4])) {
                        // Text Equality
                        const operator = filterData[3];
                        const value = filterData[4];
                        if (operator === '!') {
                            return { string: 'is not', operator: 'ne', value };
                        }
                        return { string: 'is', operator: 'exact', value };
                    }
                    if (!_.isUndefined(filterData[7])) {
                        // Numeric Comparison
                        const operator = filterData[5];
                        const value = Number(filterData[6].replace('\\.', '.'));
                        switch (operator) {
                            case '<':
                                return { string: '<', operator: 'lt', value };
                            case '<=':
                                return { string: '<=', operator: 'lte', value };
                            case '>':
                                return { string: '>', operator: 'gt', value };
                            case '>=':
                                return { string: '>=', operator: 'gte', value };
                        }
                    } else {
                        // Date Comparison
                        const operator = filterData[5];
                        const value = filterData[8];
                        switch (operator) {
                            case '<':
                                return { string: '<', operator: 'lt', value };
                            case '<=':
                                return { string: '<=', operator: 'lte', value };
                            case '>':
                                return { string: '>', operator: 'gt', value };
                            case '>=':
                                return { string: '>=', operator: 'gte', value };
                        }
                    }
                } else {
                    // Case-insensitive Contains
                    return { string: 'contains', operator: 'icontains', value: expression };
                }
            };

            const set_grid_options = (result) => {
                $scope.data = format_properties(result)
                spinner_utility.hide()
                $scope.gridOptions = {
                    data: 'data',
                    columnDefs: selected_columns(),
                    enableFiltering: true,
                    enableHorizontalScrollbar: 1,
                    cellWidth: 200,
                    enableGridMenu: true,
                    exporterMenuCsv: false,
                    exporterMenuExcel: false,
                    exporterMenuPdf: false,
                    gridMenuShowHideColumns: false,
                    gridMenuCustomItems: [{
                        title: 'Export Page to CSV',
                        action: ($event) => $scope.gridApi.exporter.csvExport('all', 'all'),
                    }],
                    onRegisterApi: (gridApi) => {
                        $scope.gridApi = gridApi;

                        gridApi.core.on.sortChanged($scope, () => {
                            spinner_utility.show()
                            _.debounce(() => {
                                updateColumnFilterSort();
                                $scope.load_inventory(1);
                            }, 500)();
                        });

                        gridApi.core.on.filterChanged($scope, _.debounce(() => {
                                spinner_utility.show()
                                updateColumnFilterSort();
                                $scope.load_inventory(1);
                            }, 2000)
                        );
                    }
                }
            }

            $scope.reset_sorts_filters = () => {
                $scope.reset_sorts()
                $scope.reset_filters()
            }
            $scope.reset_sorts = () => {
                $scope.column_sorts = []
                $scope.gridApi.core.refresh()
            }
            $scope.reset_filters = () => {
                $scope.column_filters = []
                $scope.gridApi.grid.clearAllFilters()
            }


            // -------- SUMMARY LOGIC ------------

            const summary_selected_columns = () => {
                const default_baseline = { headerCellClass: 'portfolio-summary-baseline-header', cellClass: 'portfolio-summary-baseline-cell' }
                const default_current = { headerCellClass: 'portfolio-summary-current-header', cellClass: 'portfolio-summary-current-cell' }
                const default_styles = { headerCellFilter: 'translate' }

                const baseline_cols = [
                    { field: 'baseline_cycle', displayName: 'Cycle' },
                    { field: 'baseline_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number'},
                    { field: 'baseline_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number'},
                    { field: 'baseline_weighted_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number'},
                ]
                const current_cols = [
                    { field: 'current_cycle', displayName: 'Cycle' },
                    { field: 'current_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number'},
                    { field: 'current_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number'},
                    { field: 'current_weighted_eui', displayName: `EUI (${eui_units})` , cellFilter: 'number'},
                ]
                const calc_cols = [
                    { field: 'sqft_change', displayName: 'Area % Change' },
                    {
                        field: 'eui_change', displayName: 'EUI % Improvement', cellClass: (grid, row, col, rowRenderIndex, colRenderIndex) => {
                            return row.entity.eui_change >= $scope.goal.target_percentage ? 'above-target' : 'below-target'
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
                    baseline_weighted_eui: baseline.weighted_eui,
                    current_cycle: current.cycle_name,
                    current_total_sqft: current.total_sqft,
                    current_total_kbtu: current.total_kbtu,
                    current_weighted_eui: current.weighted_eui,
                    sqft_change: summary.sqft_change,
                    eui_change: summary.eui_change,
                }]
            }

            const set_summary_grid_options = (summary) => {
                $scope.summary_data = format_summary(summary)
                $scope.summaryGridOptions = {
                    data: 'summary_data',
                    columnDefs: summary_selected_columns(),
                    enableSorting: false,
                }
            }

        }
    ]
)
