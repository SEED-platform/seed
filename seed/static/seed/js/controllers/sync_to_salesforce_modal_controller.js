/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.sync_to_salesforce_modal', []).controller('sync_to_salesforce_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'urls',
  'goal',
  'cycle_goal',
  'seed_summary_data',
  'salesforce_summary_data',
  'goal_service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, urls, goal, cycle_goal, seed_summary_data, salesforce_summary_data, goal_service) {
    $scope.goal = goal;
    $scope.goal_details = {
      Partner: $scope.goal.salesforce_partner_id,
      'Partner ID': $scope.goal.salesforce_partner_name,
      Goal: $scope.goal.salesforce_goal_id,
      'Goal ID': $scope.goal.salesforce_goal_name
    };
    console.log(seed_summary_data);
    console.log(salesforce_summary_data);

    $scope.seed_baseline_portfolio_kbtu = seed_summary_data.baseline_total_kbtu;
    $scope.salesforce_baseline_portfolio_kbtu = undefined;
    $scope.seed_baseline_portfolio_eui = seed_summary_data.baseline_weighted_eui;
    $scope.salesforce_baseline_portfolio_eui = undefined;

    $scope.baseline_cycle_goal_table = {
      'Baseline portfolio kBtu': {
        seed: seed_summary_data.baseline_total_kbtu,
        salesforce: salesforce_summary_data.baseline_portfolio_kbtu
      },
      'Baseline portfolio EUI': {
        seed: seed_summary_data.baseline_weighted_eui,
        salesforce: salesforce_summary_data.baseline_portfolio_eui
      }
    };

    $scope.cycle_goal_details = {
      'Annual Report Year': cycle_goal.salesforce_annual_report_name,
      'Annual Report ID': cycle_goal.salesforce_annual_report_id
    };

    $scope.current_cycle_goal_table = {
      'Reporting Year Start': {
        seed: cycle_goal.current_cycle.start,
        salesforce: salesforce_summary_data.reporting_year_start
      },
      'Reporting Year End': {
        seed: cycle_goal.current_cycle.end,
        salesforce: salesforce_summary_data.reporting_year_end
      },
      'Number of Properties': {
        seed: seed_summary_data.total_properties,
        salesforce: salesforce_summary_data.number_of_properties
      },
      'Portfolio Average EUI': {
        seed: seed_summary_data.current_weighted_eui,
        salesforce: salesforce_summary_data.portfolio_average_eui
      },
      'Portfolio kBtu (BBC Total Energy)': {
        seed: seed_summary_data.current_total_kbtu,
        salesforce: salesforce_summary_data.portfolio_kbtu
      },
      'New Energy Savings': {
        seed: seed_summary_data.baseline_total_kbtu - seed_summary_data.current_total_kbtu,
        salesforce: salesforce_summary_data.new_energy_savings
      },
      'El Annual Improvement': {
        seed: seed_summary_data.baseline_weighted_eui - seed_summary_data.current_weighted_eui,
        salesforce: salesforce_summary_data.ei_annual_improvement
      },
      'Total El Improvement': {
        seed: seed_summary_data.eui_change,
        salesforce: salesforce_summary_data.total_ei_improvement
      },
      'Shared Square Feet': {
        seed: seed_summary_data.shared_sqft,
        salesforce: salesforce_summary_data.shared_square_feet
      },
      'Reviewed Square Feet': {
        seed: seed_summary_data.current_total_sqft,
        salesforce: salesforce_summary_data.reviewed_square_feet
      }
    };

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };

    $scope.send_sync = () => {
      goal_service.update_salesforce($scope.goal.id, $scope.cycle_goal.id)
        .then((data) => {
          console.log(data);
        });
    };
  }
]);
