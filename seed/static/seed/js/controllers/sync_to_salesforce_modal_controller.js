/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.sync_to_salesforce_modal', []).controller('sync_to_salesforce_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'Notification',
  'urls',
  'goal',
  'latest_cycle_goal',
  'salesforce_summary_data',
  'goal_service',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, Notification, urls, goal, latest_cycle_goal, salesforce_summary_data, goal_service) {
    $scope.report_status = null;
    $scope.review_status = null;

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

    // goal details
    $scope.goal_details = {
      'Salesforce Partner': `${goal.salesforce_partner_name} (${goal.salesforce_partner_id})`,
      'Salesforce Goal': `${goal.salesforce_goal_name} (${goal.salesforce_goal_id})`
    };

    $scope.update_baseline_and_latest_report = (salesforce_summary_data) => {
      const latest_cycle_goal_summary = salesforce_summary_data[latest_cycle_goal.current_cycle.name];
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

      // latest cycle goal// latest cycle goal
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
        'EI Annual Improvement': {
          seed: latest_cycle_goal_summary.seed.baseline_weighted_eui - latest_cycle_goal_summary.seed.current_weighted_eui,
          salesforce: latest_cycle_goal_summary.salesforce.ei_annual_improvement
        },
        'Total EI Improvement': {
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

      // the 2 dropdowns (handle separately)
      $scope.report_status = latest_cycle_goal_summary.salesforce.report_status;
      $scope.review_status = latest_cycle_goal_summary.salesforce.review_status;
    };

    $scope.update_past_reports = (salesforce_summary_data) => {
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
    };

    // initialize the baseline and latest report sections of the modal
    $scope.update_baseline_and_latest_report(salesforce_summary_data);

    // initialize past reports
    $scope.update_past_reports(salesforce_summary_data);

    $scope.setMismatchHighlight = (summary, key, index) => {
      // Skip the Year column (index 0)
      if (index === 0) return false;

      const keys = Object.keys(summary);

      // Only highlight SF columns (even indices > 0) when they differ from previous SEED column
      if (index % 2 === 0 && index > 0) {
        const seedKey = keys[index - 1];
        return summary[key] !== summary[seedKey];
      }

      // Don't highlight SEED columns
      return false;
    };

    $scope.setMatchHighlight = (summary, key, index) => {
      // Skip the Year column (index 0)
      if (index === 0) return false;

      const keys = Object.keys(summary);

      // Only highlight SF columns when they match
      if (index % 2 === 0 && index > 0) {
        const seedKey = keys[index - 1];
        return summary[key] === summary[seedKey];
      }

      // Don't highlight SEED columns
      return false;
    };

    $scope.dismiss = () => {
      $uibModalInstance.close();
    };

    $scope.sync_latest_cycle = () => {
      goal_service.update_salesforce_current(goal.id, latest_cycle_goal.id, $scope.report_status ? $scope.report_status : null, $scope.review_status ? $scope.review_status : null)
        .then(() => {
          Notification.success({ message: 'Salesforce Goal and Current Annual Report Updated Successfully!', delay: 5000 });
          goal_service.get_salesforce_summary(goal.id)
            .then((data) => {
              $scope.update_baseline_and_latest_report(data.data);
            })
            .catch((error) => {
              console.error('Error retrieving Salesforce summary data:', error);
              Notification.error({ message: 'Unable to retrieve Salesforce Data to refresh the modal. Dismiss the modal and open it again.', delay: 5000 });
            });
        })
        .catch((error) => {
          console.error('Error syncing current report to Salesforce:', error);
          Notification.error({ message: 'Error Updating Salesforce Goal and Current Annual Report. ', delay: false });
        });
    };

    $scope.sync_past_cycles = () => {
      goal_service.update_salesforce_historical(goal.id, $scope.past_cycle_goals.map(([, c]) => c.id))
        .then(() => {
          Notification.success({ message: 'Salesforce historical reports updated successfully!', delay: 5000 });
          goal_service.get_salesforce_summary(goal.id)
            .then((data) => {
              $scope.update_past_reports(data.data);
            })
            .catch((error) => {
              console.error('Error retrieving Salesforce summary data:', error);
              Notification.error({ message: 'Unable to retrieve Salesforce data to refresh the modal. Dismiss the modal and open it again.', delay: 5000 });
            });
        })
        .catch((error) => {
          console.error('Error syncing historical reports to Salesforce:', error);
          Notification.error({ message: 'Error updating Salesforce historical reports. ', delay: false });
        });
    };
  }
]);
