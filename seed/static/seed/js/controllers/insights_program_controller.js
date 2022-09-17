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

      // compliance metric
      $scope.compliance_metric = {};
      // for now there should always be 1 (get_or_create_default function in compliance_metrics list api)
      // in the future there will be multiple
      if (compliance_metrics.length > 0) {
        $scope.compliance_metric = compliance_metrics[0];
      }
      console.log("COMPLIANCE METRIC: ", $scope.compliance_metric)
      console.log("ORG: ", organization_payload)

      // table row toggles
      $scope.show_properties_for_dataset = {'y': false, 'n': false, 'u': false};

      $scope.data = null;
      // chart data
      let _load_data = function () {
        if (_.isEmpty($scope.compliance_metric)) {
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
