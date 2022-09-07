angular.module('BE.seed.controller.insights_program', [])
  .controller('insights_program_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'inventory_service',
    'compliance_metrics',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      inventory_service,
      compliance_metrics,
      cycles
    ) {

      $scope.id = $stateParams.id;
      $scope.cycles = cycles.cycles;
      $scope.compliance_metric = {};

      // for now there should always be 1 (b/c of get_or_create_default function in compliance_metrics list api)
      if (compliance_metrics.length > 0) {
        $scope.compliance_metric = compliance_metrics[0];
      }


      console.log("COMPLIANCE METRIC IS THIS: ");
      console.log($scope.compliance_metric);


      // CHARTS
      var colors = [
        '#4477AA',
        '#a94455',
        '#eeeeee',
      ]

      // random default just to load the chart
      let start = '2017';
      let end = '2021';

      // override default if we have the data
      if ('start' in $scope.compliance_metric) {
        console.log("START: ", $scope.compliance_metric['start']);
        start = $scope.compliance_metric['start'].split('-')[0];
      }
      if ('end' in $scope.compliance_metric) {
        end = $scope.compliance_metric['end'].split('-')[0];
      }
      console.log("START: ", start, " END: ", end)

      // TODO placeholder just showing # properties per cycle for this org (all unknown - metric not enabled)
      const labels = []
      for (var i = Number(start); i <= Number(end);  i++) {
        labels.push(String(i));
      }
      console.log("LABELS: ", labels);

     //  const _build_chart = () => {
     //    console.log('BUILD CHART')
     //    if (!$scope.data.graph_data) {
     //      console.log('NO DATA')
     //      return
     //    }
     //    const canvas = document.getElementById('program-overview-chart')
     //    const ctx = canvas.getContext('2d')

     //    let first_axis_name = 'Number of Buildings'


     //    $scope.dataViewChart = new Chart(ctx, {
     //      type: 'bar',
     //      data: {
     //      },
     //      options: {
     //        plugins: {
     //          title: {
     //            display: true,
     //            align: 'start'
     //          },
     //          legend: {
     //            position: 'right',
     //            maxWidth: 500,
     //            labels: {
     //              boxHeight: 0,
     //              boxWidth: 50,
     //            },
     //          },
     //        },
     //        scales: {
     //          x: {
     //            stacked: true
     //          },
     //          y: {
     //            beginAtZero: true,
     //            stacked: true,
     //            position: 'left',
     //            display: false,
     //            title: {
     //              text: first_axis_name,
     //              display: true
     //            }
     //          }
     //        }
     //      }
     //    })

     //  }
    }
  ]);
