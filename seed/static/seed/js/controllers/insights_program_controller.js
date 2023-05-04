/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.insights_program', [])
  .controller('insights_program_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'compliance_metrics',
    'compliance_metric_service',
    'spinner_utility',
    'organization_payload',
    'cycles',
    'auth_payload',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      compliance_metrics,
      compliance_metric_service,
      spinner_utility,
      organization_payload,
      cycles,
      auth_payload
    ) {

      $scope.id = $stateParams.id;
      $scope.cycles = cycles.cycles;
      $scope.organization = organization_payload.organization;
      $scope.initialize_chart = true;
      $scope.auth = auth_payload.auth;

      // compliance metric
      $scope.compliance_metric = {};
      $scope.compliance_metrics = compliance_metrics;
      $scope.selected_metric = null;

      if ($scope.compliance_metrics.length > 0) {
        $scope.compliance_metric = $scope.compliance_metrics[0];
        $scope.selected_metric = $scope.compliance_metric.id;
      }

      $scope.data = null;

      $scope.updateSelectedMetric = () => {

        $scope.compliance_metric = _.find($scope.compliance_metrics, function(o) {
          return o.id == $scope.selected_metric;
        });

        // reload data for selected metric
        _load_data();

        // refresh chart
        if (!$scope.initialize_chart){
          $scope.insightsChart.update();
        }
      }

      // chart data
      let _load_data = function () {
        if (_.isEmpty($scope.compliance_metric)) {
          spinner_utility.hide();
          return;
        }
        spinner_utility.show();
        // console.log("get data for metric id: ", $scope.compliance_metric.id);
        let data = compliance_metric_service.evaluate_compliance_metric($scope.compliance_metric.id).then((data) => {
          $scope.data = data;
        }).then(() => {
          // console.log( "DATA: ", $scope.data)
          _build_chart();

        }).finally(() => {
          spinner_utility.hide()
        })
      };

      $scope.downloadChart = () => {
        var a = document.createElement('a');
        a.href = $scope.insightsChart.toBase64Image();
        a.download = 'Property Overview.png';
        a.click();
      }

      // CHARTS
      var colors = {'compliant': '#77CCCB', 'non-compliant': '#A94455', 'unknown': '#DDDDDD'}

      let _load_datasets = () => {
        // load data

        $scope.insightsChart.data.labels = $scope.data.graph_data.labels
        $scope.insightsChart.data.datasets = $scope.data.graph_data.datasets
        _.forEach($scope.insightsChart.data.datasets, function(ds) {
          ds['backgroundColor'] = colors[ds['label']]
        });

        $scope.insightsChart.update()
      }

      let _build_chart = () => {
        if (!$scope.data.graph_data) {
          return
        }

        if ($scope.initialize_chart) {
          // do this once
          // console.log("Initializing chart")
          const canvas = document.getElementById('program-overview-chart')
          const ctx = canvas.getContext('2d')

          let first_axis_name = 'Number of Buildings'

          $scope.insightsChart = new Chart(ctx, {
            type: 'bar',
            data: {
            },
            options: {
              plugins: {
                title: {
                  display: true,
                  align: 'start'
                },
                legend: {
                  display: false
                },
              },
              scales: {
                x: {
                  stacked: true
                },
                y: {
                  beginAtZero: true,
                  stacked: true,
                  position: 'left',
                  display: true,
                  title: {
                    text: first_axis_name,
                    display: true
                  }
                }
              }
            }
          });
          $scope.initialize_chart = false;
        }

        // load datasets and update chart
        _load_datasets();

      }

      setTimeout(_load_data, 0); // avoid race condition with route transition spinner.
    }
  ]);
