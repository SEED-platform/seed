/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.sync_to_salesforce_modal', []).controller('sync_to_salesforce_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'urls',
  'goal',
  'latest_cycle_goal',
  'salesforce_summary_data',
  'goal_service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, urls, goal, latest_cycle_goal, salesforce_summary_data, goal_service) {
    const latest_cycle_goal_summary = salesforce_summary_data[latest_cycle_goal.current_cycle.name];
    $scope.report_status = null;
    $scope.review_status = null;

    // goal details
    $scope.goal_details = {
      Partner: goal.salesforce_partner_id,
      'Partner ID': goal.salesforce_partner_name,
      Goal: goal.salesforce_goal_id,
      'Goal ID': goal.salesforce_goal_name
    };

    // baseline cycle goal
    $scope.baseline_cycle_goal_table = {
      'Baseline portfolio kBtu': {
        seed: latest_cycle_goal_summary.seed.baseline_total_kbtu,
        salesforce: latest_cycle_goal_summary.salesforce.baseline_portfolio_kbtu
      },
      'Baseline portfolio EUI': {
        seed: latest_cycle_goal_summary.seed.baseline_weighted_eui,
        salesforce: latest_cycle_goal_summary.salesforce.baseline_portfolio_eui
      }
    };

    // latest cycle goal
    $scope.latest_cycle_goal_table = {
      'Reporting Year Start': {
        seed: latest_cycle_goal.current_cycle.start,
        salesforce: latest_cycle_goal_summary.salesforce?.reporting_year_start
      },
      'Reporting Year End': {
        seed: latest_cycle_goal.current_cycle.end,
        salesforce: latest_cycle_goal_summary.salesforce?.reporting_year_end
      },
      'Number of Properties': {
        seed: latest_cycle_goal_summary.seed.total_properties,
        salesforce: latest_cycle_goal_summary.salesforce.number_of_properties
      },
      'Portfolio Average EUI': {
        seed: latest_cycle_goal_summary.seed.current_weighted_eui,
        salesforce: latest_cycle_goal_summary.salesforce.portfolio_average_eui
      },
      'Portfolio kBtu (BBC Total Energy)': {
        seed: latest_cycle_goal_summary.seed.current_total_kbtu,
        salesforce: latest_cycle_goal_summary.salesforce.portfolio_kbtu
      },
      'New Energy Savings': {
        seed: latest_cycle_goal_summary.seed.baseline_total_kbtu - latest_cycle_goal_summary.seed.current_total_kbtu,
        salesforce: latest_cycle_goal_summary.salesforce.new_energy_savings
      },
      'El Annual Improvement': {
        seed: latest_cycle_goal_summary.seed.baseline_weighted_eui - latest_cycle_goal_summary.seed.current_weighted_eui,
        salesforce: latest_cycle_goal_summary.salesforce.ei_annual_improvement
      },
      'Total El Improvement': {
        seed: latest_cycle_goal_summary.seed.eui_change,
        salesforce: latest_cycle_goal_summary.salesforce.total_ei_improvement
      },
      'Shared Square Feet': {
        seed: latest_cycle_goal_summary.seed.shared_sqft,
        salesforce: latest_cycle_goal_summary.salesforce.shared_square_feet
      },
      'Reviewed Square Feet': {
        seed: latest_cycle_goal_summary.seed.current_total_sqft,
        salesforce: latest_cycle_goal_summary.salesforce.reviewed_square_feet
      }
    };

    // past cycles
    $scope.past_cycle_goals = Object.entries(salesforce_summary_data).filter(
      ([k]) => k !== latest_cycle_goal.current_cycle.name
    );
    $scope.past_cycle_goals_table = $scope.past_cycle_goals.map(([, summary]) => ({
      Year: `${summary.seed.current_cycle_name} (${summary.salesforce.id})`,
      'EI Annual Improvment': summary.seed.baseline_weighted_eui - summary.seed.current_weighted_eui,
      'SF EI Annual Improvment': summary.salesforce.ei_annual_improvement,
      'Portfolio Avg EUI': summary.seed.current_weighted_eui,
      'SF Portfolio Avg EUI': summary.salesforce.portfolio_average_eui,
      'New Energy Savings': summary.seed.baseline_total_kbtu - summary.seed.current_total_kbtu,
      'SF New Energy Savings': summary.salesforce.new_energy_savings,
      'Portfolio kBtu': summary.seed.current_total_kbtu,
      'SF Portfolio kBtu': summary.salesforce.portfolio_kbtu
    }));

    $scope.report_status_options = [
      '00. Baselining',
      '00. Partner not engaged',
      '00. Partner under reengagement',
      '00. No Information Available',
      '01. No response to requests for annual data',
      '02. Partner experiencing data challenges',
      '03. Partner working on data',
      '04. Data received, under staff review',
      '05. Data returned for corrections',
      '06. Annual report reviewed by staff',
      '07. Quality check complete (industrial only)',
      '08. Finalized, ready for data display',
      '09. Data display live on web'
    ];

    $scope.review_status_options = [
      'A. Report Needed',
      'B. Report in Progress',
      'C. Report in Progress (Complex)',
      'D. Report on Hold/Partner Update Needed',
      'E. Report Completed (AM Send to Partner)',
      'F. Report and Summary Sent to Partner',
      'G. Feedback Received/Edits Needed from Data Team',
      'H. Final Report Approved for Solution Center',
      'I. Report Under Consideration for Goal Achievement',
      'J. Display Needed',
      'K. New PowerBI Needed',
      'L. Display Generated, Ready for Publish',
      'M. Display Published (AMs QC)',
      'N. AM QC Complete',
      'O. Issues for Data Team',
      'P. Data Team QC Complete',
      'Q. Opt-Out of Display'
    ];

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };

    $scope.sync_latest_cycle = () => {
      goal_service.update_salesforce(goal.id, [latest_cycle_goal.id], $scope.report_status ? $scope.report_status : null, $scope.review_status ? $scope.review_status : null)
        .then(() => {
          $uibModalInstance.close();
        });
    };

    $scope.sync_past_cycles = () => {
      goal_service.update_salesforce(goal.id, $scope.past_cycle_goals.map(([, c]) => c.id))
        .then(() => {
          $uibModalInstance.close();
        });
    };
  }
]);
