/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.insights_program', [])
  .controller('insights_program_controller', [
    '$scope',
    '$stateParams',
    '$state',
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
      $state,
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

          // build chart name
          compliance_metric_cycles = $scope.cycles.filter(c => $scope.compliance_metric.cycles.includes(c.id))
          first_cycle = compliance_metric_cycles.reduce((prev, curr) => prev.start < curr.start ? prev : curr);
          last_cycle = compliance_metric_cycles.reduce((prev, curr) => prev.end > curr.end ? prev : curr);
          cycle_range = first_cycle == last_cycle? first_cycle.name: first_cycle.name + " - " + last_cycle.name;
          $scope.chart_name = $scope.compliance_metric.name + ": " + cycle_range;
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
              onClick: (event) => {
                var activePoints = event.chart.getActiveElements(event);

                if (activePoints[0]) {
                  var activePoint = activePoints[0]
                  cycle_name = $scope.data.graph_data.labels[activePoint.index]
                  cycle = $scope.cycles.find(c => c.name == cycle_name);
                  shown_dataset_index = activePoint.datasetIndex;

                  // update locally stored insights_property configs
                  const property_configs = JSON.parse(localStorage.getItem('insights.property.configs.' + $scope.organization.id)) ?? {};
                  property_configs.compliance_metric_id = $scope.selected_metric;
                  property_configs.chart_cycle = cycle.id;
                  property_configs.dataset_visibility = [false, false, false];
                  property_configs.dataset_visibility[shown_dataset_index] = true;
                  property_configs.annotation_visibility = shown_dataset_index == 1;
                  localStorage.setItem('insights.property.configs.' + $scope.organization.id,  JSON.stringify(property_configs));

                  $state.go('insights_property');
                }
              },
              plugins: {
                title: {
                  display: true,
                  align: 'start'
                },
                legend: {
                  display: false
                },
                tooltip: {
                  callbacks: {
                    footer: tooltip_footer,
                  }
                }
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

      const tooltip_footer = (tooltipItems) => {
        const tooltipItem = tooltipItems[0];
        if (tooltipItem === undefined) return "";

        const dataIndex = tooltipItem.dataIndex;
        const barValues = $scope.insightsChart.data.datasets.map(ds => ds.data[dataIndex]);
        const barTotal = barValues.reduce((acc, curr) => acc + curr, 0);

        return ((tooltipItem.raw / barTotal) * 100).toPrecision(4) + "%";
      };

      setTimeout(_load_data, 0); // avoid race condition with route transition spinner.
    }
  ]);
