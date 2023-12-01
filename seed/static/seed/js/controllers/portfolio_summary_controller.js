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
        'current_profile',
        'property_columns',
        'uiGridConstants',
        'gridUtil',
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
            current_profile,
            property_columns,
            uiGridConstants,
            gridUtil,
        ) {
            $scope.organization = organization_payload.organization;
            $scope.cycles = cycles.cycles;
            $scope.columns = property_columns;
            $scope.access_level_tree = access_level_tree.access_level_tree;
            $scope.level_names = access_level_tree.access_level_names;
            const localStorageLabelKey = `grid.properties.labels`;
            $scope.goal = {}
            $scope.baseline_first = false;
            $scope.currentProfile = current_profile;
            
            // optionally pass a goal name to be set as $scope.goal
            const get_goals = (goal_name=false) => {
                goal_service.get_goals().then(result => {
                    $scope.goals = result.status == 'success' ? result.goals : []
                    if (goal_name) {
                        $scope.goal = $scope.goals.find(goal => goal.name == goal_name)
                    } else if ($scope.goals.length) {
                        // init - default selected goal to first
                        $scope.goal = $scope.goals[0]
                    }
                })
            }
            get_goals()
            
            // If goal changes, repopulate data
            $scope.$watch('goal', () => {
                if (!_.isEmpty($scope.goal)) {
                    $scope.valid = true
                    format_goal_details()
                    $scope.refresh_data()
                } else {
                    $scope.valid = false
                }
            })

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
                    ['Target', `${$scope.goal.target_percentage} %`],
                    ['Primary Column', get_column_name($scope.goal.column1)],
                ]
                if ($scope.goal.column2) {
                    $scope.goal_details.push(['Secondary Column', get_column_name($scope.goal.column2)])
                }
                if ($scope.goal.column3) {
                    $scope.goal_details.push(['Tertiary Column', get_column_name($scope.goal.column3)])
                }
            }

            const matching_column_names = $scope.columns.filter(col => col.is_matching_criteria).map(col => col.column_name)
            // from inventory_list_controller
            $scope.columnDisplayByName = {};
            for (const i in $scope.columns) {
                $scope.columnDisplayByName[$scope.columns[i].name] = $scope.columns[i].displayName;
            }
            
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
                new_level_instance_depth = parseInt($scope.goal.level_name_index) + 1
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth]
            }

            // GOAL EDITOR MODAL
            $scope.open_goal_editor_modal = () => {
                $scope.goal_columns = $scope.columns.filter(c => c.data_type == 'eui')
                const modalInstance = $uibModal.open({
                    templateUrl: `${urls.static_url}seed/partials/goal_editor_modal.html`,
                    controller: 'goal_editor_modal_controller',
                    size: 'lg',
                    backdrop: 'static',
                    resolve: {
                        organization: () => $scope.organization,
                        cycles: () => $scope.cycles,
                        goal_columns: () => $scope.goal_columns,
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
                $scope.summary_valid = false;

                goal_service.get_portfolio_summary($scope.goal.id).then(result => {
                    summary = result.data;
                    set_summary_grid_options(summary);
                }).then(() => {
                    $scope.summary_loading = false;
                    $scope.summary_valid = true;
                })
            }
            
            $scope.load_inventory = (page) => {
                $scope.data_loading = true;
                $scope.data_valid = false;

                let access_level_instance_id = $scope.goal.access_level_instance
                let combined_result = {}
                let per_page = 50
                let current_cycle = {id: $scope.goal.current_cycle}
                let baseline_cycle = {id: $scope.goal.baseline_cycle}
                // order of cycle property filter is dynamic based on column_sorts 
                let cycle_priority = $scope.baseline_first ? 
                    [baseline_cycle, current_cycle]: 
                    [current_cycle, baseline_cycle]

                get_paginated_properties(page, per_page, cycle_priority[0], access_level_instance_id).then(result0 => {
                    $scope.inventory_pagination = result0.pagination
                    properties = result0.results
                    combined_result[cycle_priority[0].id] = properties;
                    property_ids = properties.map(p => p.id)
                    
                    get_paginated_properties(page, per_page, cycle_priority[1], access_level_instance_id, property_ids).then(result1 => {
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

            const get_paginated_properties = (page, chunk, cycle, access_level_instance_id, include_property_ids=null) => {
                fn = inventory_service.get_properties;
                console.log('filters', $scope.column_filters)
                console.log('sorts', $scope.column_sorts)
                return fn(
                    page,
                    chunk,
                    cycle,
                    _.get($scope, 'currentProfile.id'),
                    undefined,
                    undefined,
                    true,
                    $scope.organization.id,
                    true,
                    $scope.column_filters,
                    $scope.column_sorts,
                    false,
                    undefined,
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
                const gfa = $scope.columns.find(col => col.column_name == 'gross_floor_area')
                const preferred_columns = [$scope.columns.find(c => c.id == $scope.goal.column1)]
                if ($scope.goal.column2) preferred_columns.push($scope.columns.find(c => c.id == $scope.goal.column2))
                if ($scope.goal.column3) preferred_columns.push($scope.columns.find(c => c.id == $scope.goal.column3))
                
                const baseline_cycle_name = $scope.cycles.find(c => c.id == $scope.goal.baseline_cycle).name
                const current_cycle_name = $scope.cycles.find(c => c.id == $scope.goal.current_cycle).name
                // some fields span cycles (id, name, type)
                // and others are cycle specific (source EUI, sqft)
                let current_properties = properties[$scope.goal.current_cycle]
                let baseline_properties = properties[$scope.goal.baseline_cycle]
                let flat_properties = $scope.baseline_first ?
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
                        property.baseline_sqft = baseline[gfa.name]
                    }
                    // add current stats
                    if (current) {
                        property.current_cycle = current_cycle_name
                        property.current_sqft = current[gfa.name]
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
                    { field: 'baseline_cycle', displayName: 'Cycle' },
                    { field: 'baseline_sqft', displayName: 'Sq. FT' },
                    { field: 'baseline_eui', displayName: 'EUI' },
                    { field: 'baseline_kbtu', displayName: 'kBTU' },
                    build_label_col_def('baseline-labels', 'baseline')
                ]
                const current_cols = [
                    { field: 'current_cycle', displayName: 'Cycle' },
                    { field: 'current_sqft', displayName: 'Sq. FT' },
                    { field: 'current_eui', displayName: 'EUI' },
                    { field: 'current_kbtu', displayName: 'kBTU' },
                    build_label_col_def('current-labels', 'current')
                ]
                const summary_cols = [
                    { field: 'sqft_change', displayName: 'Sq Ft % Change' },
                    { field: '\eui_change', displayName: 'EUI % Improvement' },
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

            const format_cycle_column = (column) => {
                /* filtering is based on existing db columns. 
                ** The PortfilioSummary uses cycle specific columns that do not exist elsewhere ('baseline_eui', 'current_sqft')
                ** To sort on these columns, override the column name to the cannonical column, and set the cycle filter order
                ** ex: if sort = {name: 'baseline_sqft'}, set {name: 'gross_floor_area_##'} and filter for baseline properties frist.

                ** NOTE: 
                ** cant fitler on cycle - cycle is not a column
                ** cant filter on kbtu - not a real column. calc'ed from eui and sqft
                */
                let eui_column = $scope.columns.find(c => c.id == $scope.goal.column1)
                let gfa_column = $scope.columns.find(c => c.column_name == 'gross_floor_area')
                
                const cycle_column_lookup = {
                    'baseline_eui': eui_column.name,
                    'baseline_sqft': gfa_column.name,
                    'current_eui': eui_column.name,
                    'current_sqft': gfa_column.name,
                }
                if (cycle_column_lookup[column.name]) {
                    $scope.baseline_first = column.name.includes('baseline')
                    column.name = cycle_column_lookup[column.name]
                }
                
                return column

            }
            // from inventory_list_controller
            const updateColumnFilterSort = () => {
                const columns = _.filter($scope.gridApi.saveState.save().columns, (col) => _.keys(col.sort).filter((key) => key !== 'ignoreSort').length + (_.get(col, 'filters[0].term', '') || '').length > 0);

                // inventory_service.saveGridSettings(`${localStorageKey}.sort`, {
                //     columns
                // });
                // let columns = $scope.gridApi.grid.columns
                $scope.column_filters = [];
                // $scope.column_sorts = [];
                // parse the filters and sorts
                for (let column of columns) {
                    // format column if cycle specific
                    column = format_cycle_column(column)
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
                $scope.gridOptions = {
                    data: 'data',
                    columnDefs: selected_columns(),
                    enableFiltering: true,
                    enableHorizontalScrollbar: 1,
                    cellWidth: 200,
                    onRegisterApi: (gridApi) => {
                        $scope.gridApi = gridApi;

                        gridApi.core.on.sortChanged($scope, () => {
                            updateColumnFilterSort();
                            $scope.load_inventory(1);
                        });
                        gridApi.core.on.filterChanged(
                            $scope,
                            _.debounce(() => {
                                updateColumnFilterSort();
                                $scope.load_inventory(1);
                            }, 2000)
                        );
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
                    { field: 'baseline_weighted_eui', displayName: 'EUI' },
                ]
                const current_cols = [
                    { field: 'current_cycle', displayName: 'Cycle' },
                    { field: 'current_total_sqft', displayName: 'Total Sq. FT' },
                    { field: 'current_total_kbtu', displayName: 'Total kBTU' },
                    { field: 'current_weighted_eui', displayName: 'EUI' },
                ]
                const calc_cols = [
                    { field: 'sqft_change', displayName: 'Sq. FT % Change' },
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
                    columnDefs: summary_selected_columns()
                }
            }

        }
    ]
)