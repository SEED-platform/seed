/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_summary', [])
  .controller('inventory_summary_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'analyses_service',
    'inventory_service',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      analyses_service,
      inventory_service,
      cycles_payload,
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      // charts is where we will store references to our charts
      const charts = {};

      const lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: _.find(cycles_payload.cycles, {id: lastCycleId}) || _.first(cycles_payload.cycles),
        cycles: cycles_payload.cycles
      };

      const draw_charts = function() {
        const chartConfigs = [
          { name: 'property_types', x: 'extra_data__Largest Property Use Type', y: 'count', xLabel: 'Property Types'},
          { name: 'year_built', x: 'year_built', y: 'percentage', xLabel: 'Year Built' },
          { name: 'energy', x: 'site_eui', y: 'percentage', xLabel: 'Site EUI' },
          { name: 'square_footage', x: 'gross_floor_area', y: 'percentage' , xLabel: 'Gross Floor Area'},
        ]

        if (_.isEmpty(charts)) {
          // initialize charts
          chartConfigs.forEach(config => {
            const svg = dimple.newSvg("#chart", 500, 750);
            const chart = new dimple.chart(svg, []);
            const xaxis = chart.addCategoryAxis('x', config.x);
            xaxis.title = config.xLabel;
            chart.addMeasureAxis('y', config.y);
            chart.addSeries(null, dimple.plot.bar);
            charts[config.name] = chart;
          })
        }

        chartConfigs.forEach(config => {
          const chart = charts[config.name]
          chart.data = $scope.summary_data[config.name]
          if ($scope.summary_data[config.name].length > 0) {
            chart.svg.select('.missing-data').remove()
          } else {
            chart.svg
              .append('text')
              .attr('class', 'missing-data')
              .attr('x', 100)
              .attr('y', 100)
              .attr('dy', '2em')
              .text('Insufficient number of properties to summarize')
          }
          chart.draw();
        })
      }

      const refresh_data = function () {
        $scope.progress = {};
        const modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/inventory_loading_modal.html',
          backdrop: 'static',
          windowClass: 'inventory-progress-modal',
          scope: $scope
        });

        analyses_service.get_summary($scope.cycle.selected_cycle.id)
          .then(function(data) {
            $scope.summary_data = data;
            $scope.table_data = [
              {
                text: "Total Records",
                count: data['total_records']
              },{
                text: "Number of Extra Data Fields",
                count: data['number_extra_data_fields']
              }
            ];

            draw_charts();
            modalInstance.close()
          })
      };

      $scope.update_cycle = function (cycle) {
        inventory_service.save_last_cycle(cycle.id);
        $scope.cycle.selected_cycle = cycle;
        refresh_data();
      };

      // load initial data
      refresh_data()
    }
  ]);
