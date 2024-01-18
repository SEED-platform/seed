/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.insights_program', []).controller('insights_program_controller', [
  '$scope',
  '$stateParams',
  '$state',
  '$uibModal',
  'urls',
  'compliance_metrics',
  'compliance_metric_service',
  'spinner_utility',
  'organization_payload',
  'filter_groups',
  'cycles',
  'property_columns',
  'auth_payload',
  // eslint-disable-next-line func-names
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
    filter_groups,
    cycles,
    property_columns,
    auth_payload
  ) {
    $scope.id = $stateParams.id;
    $scope.cycles = cycles.cycles;
    $scope.organization = organization_payload.organization;
    $scope.initialize_chart = true;
    $scope.auth = auth_payload.auth;

    // used by modal
    $scope.filter_groups = filter_groups;
    $scope.property_columns = property_columns;

    // compliance metric
    $scope.compliance_metric = {};
    $scope.compliance_metrics = compliance_metrics;
    $scope.selected_metric = null;

    if ($scope.compliance_metrics.length > 0) {
      $scope.compliance_metric = $scope.compliance_metrics[0];
      $scope.selected_metric = $scope.compliance_metric.id;
    }

    $scope.data = null;

    $scope.downloadChart = () => {
      const a = document.createElement('a');
      a.href = $scope.insightsChart.toBase64Image();
      a.download = 'Property Overview.png';
      a.click();
    };

    // CHARTS
    const colors = { compliant: '#77CCCB', 'non-compliant': '#A94455', unknown: '#DDDDDD' };

    // Program Setup Modal
    $scope.open_program_setup_modal = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/program_setup.html`,
        controller: 'program_setup_controller',
        size: 'lg',
        backdrop: 'static',
        resolve: {
          cycles: () => $scope.cycles,
          compliance_metrics: () => $scope.compliance_metrics,
          organization_payload: () => $scope.organization,
          filter_groups: () => $scope.filter_groups,
          property_columns: () => $scope.property_columns,
          id: () => $scope.selected_metric
        }
      });
      // on modal close
      modalInstance.result.then((program) => {
        // re-fetch compliance metrics
        compliance_metric_service.get_compliance_metrics($scope.organization.id).then((data) => {
          $scope.compliance_metrics = data;
          // change selection to last selected in modal and reload
          if ($scope.compliance_metrics.length > 0) {
            if (program != null) {
              $scope.compliance_metric = $scope.compliance_metrics.find((cm) => cm.id === program.id);
              $scope.selected_metric = program.id;
            } else {
              // attempt to keep the selected metric
              $scope.compliance_metric = $scope.compliance_metrics.find((cm) => cm.id === $scope.selected_metric);
              if ($scope.compliance_metric == null) {
                // load first metric b/c selected metric no longer exists
                $scope.compliance_metric = $scope.compliance_metrics[0];
                $scope.selected_metric = $scope.compliance_metric.id;
              }
            }
          } else {
            // load nothing
            $scope.compliance_metric = {};
            $scope.selected_metric = null;
            $scope.data = null;
          }

          $scope.updateSelectedMetric();
        });
      });
    };

    const _load_datasets = () => {
      // load data

      $scope.insightsChart.data.labels = $scope.data.graph_data.labels;
      $scope.insightsChart.data.datasets = $scope.data.graph_data.datasets;
      _.forEach($scope.insightsChart.data.datasets, (ds) => {
        ds.backgroundColor = colors[ds.label];
      });

      $scope.insightsChart.update();
    };

    const tooltip_footer = (tooltipItems) => {
      const tooltipItem = tooltipItems[0];
      if (tooltipItem === undefined) return '';

      const { dataIndex } = tooltipItem;
      const barValues = $scope.insightsChart.data.datasets.map((ds) => ds.data[dataIndex]);
      const barTotal = barValues.reduce((acc, curr) => acc + curr, 0);

      return `${((tooltipItem.raw / barTotal) * 100).toPrecision(4)}%`;
    };

    const _build_chart = () => {
      if (!$scope.data.graph_data) {
        return;
      }

      if ($scope.initialize_chart) {
        // do this once
        // console.log("Initializing chart")
        const canvas = document.getElementById('program-overview-chart');
        const ctx = canvas.getContext('2d');

        const first_axis_name = 'Number of Buildings';

        $scope.insightsChart = new Chart(ctx, {
          type: 'bar',
          data: {},
          options: {
            onClick: (event) => {
              const activePoints = event.chart.getActiveElements(event);

              if (activePoints[0]) {
                const activePoint = activePoints[0];
                const cycle_name = $scope.data.graph_data.labels[activePoint.index];
                const cycle = $scope.cycles.find((c) => c.name === cycle_name);
                const shown_dataset_index = activePoint.datasetIndex;

                // update locally stored insights_property configs
                const property_configs = JSON.parse(localStorage.getItem(`insights.property.configs.${$scope.organization.id}`)) ?? {};
                property_configs.compliance_metric_id = $scope.selected_metric;
                property_configs.chart_cycle = cycle.id;
                property_configs.dataset_visibility = [false, false, false];
                property_configs.dataset_visibility[shown_dataset_index] = true;
                property_configs.annotation_visibility = shown_dataset_index === 1;
                localStorage.setItem(`insights.property.configs.${$scope.organization.id}`, JSON.stringify(property_configs));

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
                  footer: tooltip_footer
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
    };

    // chart data
    const _load_data = () => {
      if (_.isEmpty($scope.compliance_metric)) {
        spinner_utility.hide();
        return;
      }
      spinner_utility.show();
      // console.log("get data for metric id: ", $scope.compliance_metric.id);
      compliance_metric_service
        .evaluate_compliance_metric($scope.compliance_metric.id)
        .then((data) => {
          $scope.data = data;
        })
        .then(() => {
          // console.log( "DATA: ", $scope.data)
          _build_chart();

          // build chart name
          const compliance_metric_cycles = $scope.cycles.filter((c) => $scope.compliance_metric.cycles.includes(c.id));
          const first_cycle = compliance_metric_cycles.reduce((prev, curr) => (prev.start < curr.start ? prev : curr));
          const last_cycle = compliance_metric_cycles.reduce((prev, curr) => (prev.end > curr.end ? prev : curr));
          const cycle_range = first_cycle === last_cycle ? first_cycle.name : `${first_cycle.name} - ${last_cycle.name}`;
          $scope.chart_name = `${$scope.compliance_metric.name}: ${cycle_range}`;
        })
        .finally(() => {
          spinner_utility.hide();
        });
    };

    $scope.updateSelectedMetric = () => {
      $scope.compliance_metric = {};
      if ($scope.selected_metric != null) {
        $scope.compliance_metric = _.find($scope.compliance_metrics, (o) => o.id === $scope.selected_metric);
      }

      // reload data for selected metric
      _load_data();

      // refresh chart
      if (!$scope.initialize_chart) {
        $scope.insightsChart.update();
      }
    };

    setTimeout(_load_data, 0); // avoid race condition with route transition spinner.
  }
]);
