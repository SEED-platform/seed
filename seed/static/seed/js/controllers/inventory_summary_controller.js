/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
      cycles_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;

      const lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: _.find(cycles_payload.cycles, {id: lastCycleId}) || _.first(cycles_payload.cycles),
        cycles: cycles_payload.cycles
      };

      $scope.charts = [
        {
          name: 'property_types',
          chart: null,
          x: 'extra_data__Largest Property Use Type',
          y: 'count',
          xLabel: 'Property Types'
        }, {
          name: 'year_built',
          chart: null,
          x: 'year_built',
          y: 'percentage',
          xLabel:
          'Year Built'
        }, {
          name: 'energy',
          chart: null,
          x: 'site_eui',
          y: 'percentage',
          xLabel: 'Site EUI'
        }, {
          name: 'square_footage',
          chart: null,
          x: 'gross_floor_area',
          y: 'percentage',
          xLabel: 'Gross Floor Area'
        }
      ];
      let charts_loaded = false;

      const load_charts = function () {
        if (!charts_loaded) {
          charts_loaded = true;
          $scope.charts.forEach(config => {
            const svg = dimple.newSvg('#chart-' + config.name, '100%', 500);
            const chart = new dimple.chart(svg, []);
            const xaxis = chart.addCategoryAxis('x', config.x);
            xaxis.title = config.xLabel;
            chart.addMeasureAxis('y', config.y);
            chart.addSeries(null, dimple.plot.bar);
            $scope.charts[config.name] = chart;
          });
        }

        $scope.charts.forEach(config => {
          const chart = $scope.charts[config.name];
          if ($scope.summary_data[config.name].length < 1) {
            return;
          }
          chart.data = $scope.summary_data[config.name];
          chart.svg.select('.missing-data').remove();
          $scope.draw_chart(config.name, false);
        });
      };

      $scope.draw_chart = function (chart_name, no_data_change = true) {
        if ($scope.summary_data[chart_name].length < 1) {
          return;
        }
        setTimeout(() => {
          $scope.charts[chart_name].draw(0, no_data_change);
        }, 50);
      };

      const refresh_data = function () {
        $scope.progress = {};
        const modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/inventory_loading_modal.html',
          backdrop: 'static',
          windowClass: 'inventory-progress-modal',
          scope: $scope
        });

        analyses_service.get_summary($scope.cycle.selected_cycle.id)
          .then(function (data) {
            $scope.summary_data = data;
            $scope.table_data = [
              {
                text: 'Total Records',
                count: data.total_records
              }, {
                text: 'Number of Extra Data Fields',
                count: data.number_extra_data_fields
              }
            ];

            const column_settings_count = data['column_settings fields and counts'];
            $scope.column_settings_count = Object.entries(column_settings_count).map(([key, value]) => {
              return {
                column_settings: key,
                count: value
              };
            });

            load_charts();
            modalInstance.close();
          });
      };

      $scope.update_cycle = function (cycle) {
        inventory_service.save_last_cycle(cycle.id);
        $scope.cycle.selected_cycle = cycle;
        refresh_data();
      };

      // load initial data
      refresh_data();
    }
  ]);
