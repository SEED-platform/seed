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
        'cycles',
        'property_columns',
        'spinner_utility',
        function (
            $scope,
            $state,
            $stateParams,
            inventory_service,
            cycles,
            property_columns,
            spinner_utility,
        ) {
            $scope.cycles = cycles.cycles;
            $scope.columns = property_columns;
            $scope.valid = false;
            $scope.data = [];
            $scope.summary_data = [];

            const cycle_column_keys = ['gross_floor_area', 'site_eui',]
            const cycle_column_vals = property_columns.filter(c => cycle_column_keys.includes(c.column_name)).map(c => c.name)
            // convert column_name to name
            const cycle_column_lookup = Object.fromEntries(_.zip(cycle_column_keys, cycle_column_vals))

            const site_eui_column = property_columns.find(col => col.column_name == 'site_eui');
            $scope.dataReview = {
                goal_column: site_eui_column.id,
                goal: 0,
                // baseline_cycle: $scope.cycles[0],
                // current_cycle: $scope.cycles.at(-1)
            };


            $scope.refresh_data = () => {
                console.log('refresh_data')
                expected_keys = ['baseline_cycle', 'current_cycle', 'goal', 'goal_column']
                valid = expected_keys.every(key => key in $scope.dataReview)
                if (!valid) {
                    console.log('not valid')
                    return
                }
                spinner_utility.show()
                $scope.valid = true;
                const cycle_ids = [$scope.dataReview.baseline_cycle.id, $scope.dataReview.current_cycle.id]

                inventory_service.properties_cycle(undefined, cycle_ids).then(result => {
                    $scope.data = format_properties(result)
                    $scope.summary_data = format_summary()
                    // $scope.updateHeight()
                }).then(() => { spinner_utility.hide() })
                console.log('valid')
            }
            $scope.refresh_data()

            const format_properties = (properties) => {
                // properties = {cycle_id1: [properties1], cycle_id2: [properties2]}. 
                // there are some fields that span cycles (id, name, type)
                // and others are cycle specific (site EUI, sqft)

                let baseline_properties = properties[$scope.dataReview.baseline_cycle.id]
                let current_properties = properties[$scope.dataReview.current_cycle.id]
                let flat_properties = [...baseline_properties, ...current_properties].flat()
                let unique_ids = [...new Set(flat_properties.map(property => property.id))]
                let site_eui = cycle_column_lookup.site_eui
                let gfa = cycle_column_lookup.gross_floor_area
                let combined_properties = []
                unique_ids.forEach(id => {
                    // find matching properties
                    let base = baseline_properties.find(p => p.id == id)
                    let current = current_properties.find(p => p.id == id)
                    // set accumulator
                    let property = base || current

                    // add baseline stats
                    property.baseline_period = $scope.dataReview.baseline_cycle.end
                    property.baseline_sqft = base && base[gfa]
                    property.baseline_site_eui = base && base[site_eui]
                    property.baseline_kbtu = Math.round(property.baseline_sqft * property.baseline_site_eui) || undefined
                    // add current stats
                    property.current_period = $scope.dataReview.current_cycle.end
                    property.current_sqft = current && current[gfa]
                    property.current_site_eui = current && current[site_eui]
                    property.current_kbtu = Math.round(property.current_sqft * property.current_site_eui) || undefined
                    // comparison stats
                    property.site_eui_change = percentage(property.baseline_site_eui, property.current_site_eui)
                    property.sqft_change = percentage(property.current_sqft, property.baseline_sqft)

                    combined_properties.push(property)

                })
                return combined_properties
            }


            const format_summary = () => {
                // summary consists of baseline/current total sqft, total kbtu, weigthed eui 
                // calc percentage for sqft change and eui improvment
                let baseline_total_sqft = 0
                let baseline_total_kbtu = 0
                let current_total_sqft = 0
                let current_total_kbtu = 0

                $scope.data.forEach(row => {
                    baseline_total_sqft += row.baseline_sqft || 0
                    baseline_total_kbtu += row.baseline_kbtu || 0
                    current_total_sqft += row.current_sqft || 0
                    current_total_kbtu += row.current_kbtu || 0
                })
                let baseline_weighted_site_eui = Math.round(baseline_total_kbtu / baseline_total_sqft)
                let current_weighted_site_eui = Math.round(current_total_kbtu / current_total_sqft)
                let sqft_change = percentage(current_total_sqft, baseline_total_sqft)
                let eui_change = percentage(baseline_weighted_site_eui, current_weighted_site_eui)

                return [{
                    baseline_period: $scope.dataReview.baseline_cycle.end,
                    baseline_total_sqft,
                    baseline_total_kbtu,
                    baseline_weighted_site_eui,
                    current_period: $scope.dataReview.current_cycle.end,
                    current_total_sqft,
                    current_total_kbtu,
                    current_weighted_site_eui,
                    sqft_change,
                    eui_change,
                }]
            }

            const percentage = (a, b) => {
                return Math.round((a - b) / a * 100)
            }

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
                const default_baseline = { headerCellClass: 'data-review-baseline-header', cellClass: 'data-review-baseline-cell' }
                const default_current = { headerCellClass: 'data-review-current-header', cellClass: 'data-review-current-cell' }
                const default_styles = { headerCellFilter: 'translate', minWidth: 75, width: 150 }

                cols.forEach(col => col.parentColumn = 'parent')
                const baseline_cols = [
                    { field: 'baseline_period', displayName: 'Period' },
                    { field: 'baseline_sqft', displayName: 'Sq. FT' },
                    { field: 'baseline_site_eui', displayName: 'Site EUI' },
                    { field: 'baseline_kbtu', displayName: 'kBTU' },
                ]
                const current_cols = [
                    { field: 'current_period', displayName: 'Period' },
                    { field: 'current_sqft', displayName: 'Sq. FT' },
                    { field: 'current_site_eui', displayName: 'Site EUI' },
                    { field: 'current_kbtu', displayName: 'kBTU' },
                ]
                const summary_cols = [
                    { field: 'site_eui_change', displayName: 'Site EUI % Improvement' },
                    { field: 'sqft_change', displayName: 'Sq Ft % Change' },
                ]

                apply_defaults(baseline_cols, default_baseline)
                apply_defaults(current_cols, default_current)
                cols = [...cols, ...baseline_cols, ...current_cols, ...summary_cols]

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
                return cols

            }
            // $scope.updateHeight = function () {
            //     console.log('update height')
            //     let entries = $scope.data.length 
            //     let calc_height = entries * 30 + 58
            //     let window_height = window.innerHeight - 400
            //     let height = calc_height > (window.innerHeight - 400) ? window_height : calc_height

            //     $scope.gridHeight =  600 + 'px'
            //     // $scope.gridHeight =  height + 'px'
            // };

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

            const summary_selected_columns = () => {
                const default_baseline = { headerCellClass: 'data-review-baseline-header', cellClass: 'data-review-baseline-cell' }
                const default_current = { headerCellClass: 'data-review-current-header', cellClass: 'data-review-current-cell' }
                const default_styles = { headerCellFilter: 'translate' }

                const baseline_cols = [
                    { field: 'baseline_period', displayName: 'Period (Baseline)' },
                    { field: 'baseline_total_sqft', displayName: 'Total Sq. FT (Baseline)' },
                    { field: 'baseline_total_kbtu', displayName: 'Total kBTU (Baseline)' },
                    { field: 'baseline_weighted_site_eui', displayName: 'Site Eui (Baseline)' },
                ]
                const current_cols = [
                    { field: 'current_period', displayName: 'Period (Current)' },
                    { field: 'current_total_sqft', displayName: 'Total Sq. FT (Current)' },
                    { field: 'current_total_kbtu', displayName: 'Total kBTU (Current)' },
                    { field: 'current_weighted_site_eui', displayName: 'Site Eui (Current)' },
                ]
                const calc_cols = [
                    { field: 'sqft_change', displayName: 'Sq. FT % Change' },
                    {
                        field: 'eui_change', displayName: 'EUI % Improvement', cellClass: (grid, row, col, rowRenderIndex, colRenderIndex) => {
                            return row.entity.eui_change >= $scope.dataReview.goal ? 'above-target' : 'below-target'
                        }
                    },
                ]
                apply_defaults(baseline_cols, default_baseline, default_styles)
                apply_defaults(current_cols, default_current, default_styles)
                apply_defaults(calc_cols)

                return [...baseline_cols, ...current_cols, ...calc_cols]
            }

            $scope.summaryGridOptions = {
                data: 'summary_data',
                columnDefs: summary_selected_columns()
            }

        }
    ]
    )