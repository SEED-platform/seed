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
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      compliance_metrics,
      compliance_metric_service,
      spinner_utility,
      organization_payload,
      cycles
    ) {

      $scope.id = $stateParams.id;
      $scope.cycles = cycles.cycles;
      $scope.organization = organization_payload.organization;
      $scope.initialize_chart = true;

      // compliance metric
      $scope.compliance_metric = {};
      $scope.compliance_metrics = compliance_metrics;
      $scope.selected_metric = null;

      if ($scope.compliance_metrics.length > 0) {
        $scope.compliance_metric = $scope.compliance_metrics[0];
        $scope.selected_metric = $scope.compliance_metric.id;
      }

      // table row toggles
      $scope.show_properties_for_dataset = {'y': false, 'n': false, 'u': false};

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
          console.log("DATA: ", data);
          spinner_utility.hide();
        }).then(() => {
          // console.log( "DATA: ", $scope.data)
          _build_chart();

        })
      };

      $scope.downloadChart = () => {
        var a = document.createElement('a');
        a.href = $scope.insightsChart.toBase64Image();
        a.download = 'Property Overview.png';
        a.click();
      }

      $scope.get_display_field_value = function(cycle_id, prop_id) {
        let name = null
        let record = _.find($scope.data.properties_by_cycles[cycle_id], {'property_view_id': prop_id})
        if (record) {
          name = _.find(record, function(v,k) {
            return _.startsWith(k, $scope.organization.property_display_field)
          });
        }

        return name ? name : prop_id
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
        // console.log("CHART DATA: ", $scope.insightsChart.data)

      }

      let _build_chart = () => {
        console.log('BUILD CHART')
        if (!$scope.data.graph_data) {
          console.log('NO DATA')
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

      _load_data();
    }
  ]);
