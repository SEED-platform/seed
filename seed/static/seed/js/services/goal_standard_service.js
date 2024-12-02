/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.goal_standard', []).factory('goal_standard_service', [
    '$http',
    'user_service',
    (
        $http,
        user_service
    ) => {
        const goal_standard_service = {};

        goal_standard_service.test = () => {
            return 'DOG'
        }

        goal_standard_service.data_report_details = (data_report, goal0, access_level_instance) => {
            const commitment_sqft = data_report.commitment_sqft?.toLocaleString() || 'n/a';
            const data_report_details = [
                { // column 1
                    'Baseline Cycle': data_report.baseline_cycle_name,
                    'Current Cycle': data_report.current_cycle_name,
                    [data_report.level_name]: access_level_instance,
                    'Total Properties': goal0.current_cycle_property_view_ids.length,  // RP TEMP
                    'Commitment Sq. Ft': commitment_sqft
                },
                { // column 2
                    'Portfolio Target': `${data_report.target_percentage} %`,
                    'Area Column': goal0.area_column_name,
                    'Primary EUI': goal0.eui_column1_name
                }
            ];
            if (data_report.eui_column2) {
                data_report_details[1]['Secondary EUI'] = data_report.goal.eui_column2_name;
            }
            if (data_report.eui_column3) {
                data_report_details[1]['Tertiary EUI'] = $scope.data_report.goal.eui_column3_name;
            }

            return data_report_details
        }
        
        const apply_defaults = (cols, ...defaults) => {
            _.map(cols, (col) => _.defaults(col, ...defaults));
        };

        goal_standard_service.data_report_stats = (summary, data_report) => {
            const passing_sqft = summary.current ? summary.current.total_sqft : null;
            // show help text if less than {50}% of properties are passing checks
            const data_report_stats = [
                { name: 'Commitment (Sq. Ft)', value: data_report.commitment_sqft },
                { name: 'Shared (Sq. Ft)', value: summary.shared_sqft },
                { name: 'Passing Checks (Sq. Ft)', value: passing_sqft },
                { name: 'Passing Checks (% of committed)', value: summary.passing_committed },
                { name: 'Passing Checks (% of shared)', value: summary.passing_shared },
                { name: 'Total Passing Checks', value: summary.total_passing },
                { name: 'Total New or Acquired', value: summary.total_new_or_acquired }
            ];
        }

        goal_standard_service.summary_column_defs = (goal0, area_units, eui_units) => {
            const default_baseline = { headerCellClass: 'portfolio-summary-baseline-header', cellClass: 'portfolio-summary-baseline-cell' };
            const default_current = { headerCellClass: 'portfolio-summary-current-header', cellClass: 'portfolio-summary-current-cell' };
            const default_styles = { headerCellFilter: 'translate' };

            const baseline_cols = [
                { field: 'baseline_cycle', displayName: 'Cycle' },
                { field: 'baseline_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number' },
                { field: 'baseline_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number' },
                { field: 'baseline_weighted_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number' }
            ];
            const current_cols = [
                { field: 'current_cycle', displayName: 'Cycle' },
                { field: 'current_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number' },
                { field: 'current_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number' },
                { field: 'current_weighted_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number' }
            ];
            const calc_cols = [
                { field: 'sqft_change', displayName: 'Area % Change' },
                {
                    field: 'eui_change',
                    displayName: 'EUI % Improvement',
                    cellClass: (grid, row) => (row.entity.eui_change >= goal0.target_percentage ? 'above-target' : 'below-target')
                }
            ];
            apply_defaults(baseline_cols, default_baseline, default_styles);
            apply_defaults(current_cols, default_current, default_styles);
            apply_defaults(calc_cols);

            return [...baseline_cols, ...current_cols, ...calc_cols].map((col) => ({
                ...col,
                minWidth: 50
            }));

        }

        goal_standard_service.format_summary = (summary, data_report_details) => {
            data_report_details[0]['Total Properties'] = summary.total_properties.toLocaleString();
            const baseline = summary.baseline;
            const current = summary.current;
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
                eui_change: summary.eui_change
            }];
        }

        return goal_standard_service;
    }
]);