angular.module('BE.seed.controller.insights_program', [])
  .controller('insights_program_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'compliance_metrics',
    'compliance_metric_service',
    'spinner_utility',
    'organization_id',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      compliance_metrics,
      compliance_metric_service,
      spinner_utility,
      organization_id,
      cycles
    ) {

      $scope.id = $stateParams.id;
      $scope.cycles = cycles.cycles;
      $scope.organization_id = organization_id;

      // compliance metric
      $scope.compliance_metric = {};
      // for now there should always be 1 (get_or_create_default function in compliance_metrics list api)
      // in the future there will be multiple
      if (compliance_metrics.length > 0) {
        $scope.compliance_metric = compliance_metrics[0];
      }
      console.log("COMPLIANCE METRIC: ")
      console.log($scope.compliance_metric)

      // table row toggles
      $scope.show_properties_for_dataset = {'y': false, 'n': false, 'u': false};

      // chart data
      $scope.data = {};
      let _load_data = function () {
        if (!$scope.compliance_metric) {
          spinner_utility.hide();
          return;
        }
        spinner_utility.show();
        let data = compliance_metric_service.evaluate_compliance_metric($scope.compliance_metric.id).then((data) => {
          $scope.data = data;
          spinner_utility.hide();
        }).then(() => {
          console.log( "DATA: ", $scope.data)
          _build_chart();

        })
      };

      // CHARTS
      var colors = {'compliant': '#77CCCB', 'non-compliant': '#A94455', 'unknown': '#EEEEEE'}

      const _build_chart = () => {
        console.log('BUILD CHART')
        if (!$scope.data.graph_data) {
          console.log('NO DATA')
          return
        }
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

        // load data
        console.log('load dataset start')
        $scope.insightsChart.data.labels = $scope.data.graph_data.labels
        $scope.insightsChart.data.datasets = $scope.data.graph_data.datasets
        _.forEach($scope.insightsChart.data.datasets, function(ds) {
          ds['backgroundColor'] = colors[ds['label']]
        });

        $scope.insightsChart.update()
        console.log('_assign_data COMPLETE ')
        console.log("CHART DATA: ", $scope.insightsChart.data)

      }

      _load_data();
    }
  ]);
