/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_plots', [])
  .controller('inventory_plots_controller', [
    '$scope',
    '$filter',
    '$window',
    '$uibModal',
    '$sce',
    '$state',
    '$stateParams',
    '$q',
    'inventory_service',
    'label_service',
    'data_quality_service',
    'geocode_service',
    'user_service',
    'derived_columns_service',
    'Notification',
    'cycles',
    'profiles',
    'current_profile',
    'all_columns',
    'derived_columns_payload',
    'urls',
    'spinner_utility',
    'naturalSort',
    '$translate',
    'uiGridConstants',
    'i18nService', // from ui-grid
    'organization_payload',
    'gridUtil',
    function (
      $scope,
      $filter,
      $window,
      $uibModal,
      $sce,
      $state,
      $stateParams,
      $q,
      inventory_service,
      label_service,
      data_quality_service,
      geocode_service,
      user_service,
      derived_columns_service,
      Notification,
      cycles,
      profiles,
      current_profile,
      all_columns,
      derived_columns_payload,
      urls,
      spinner_utility,
      naturalSort,
      $translate,
      uiGridConstants,
      i18nService,
      organization_payload,
      gridUtil
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      var lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: _.find(cycles.cycles, { id: lastCycleId }) || _.first(cycles.cycles),
        cycles: cycles.cycles
      };

      var createChart = function (elementId, xAxisKey, yAxisKey, onHover) {
        var canvas = document.getElementById(elementId);
        var ctx = canvas.getContext("2d");

        return new Chart(ctx, {
          type: 'scatter',
          data: {
            datasets: [{
              data: [],
              backgroundColor: "cyan",
              hoverBackgroundColor: 'red',
              borderColor: "black",
            }],
          },
          options: {
            scales: {
              x: {
                display: true,
                title: {
                  display: true,
                  text: xAxisKey,
                },
              },
              y: {
                display: true,
                title: {
                  display: true,
                  text: yAxisKey
                }
              }
            },
            plugins: {
              zoom: {
                limits: {
                  x: { min: 'original', max: 'original', minRange: 50 },
                  y: { min: 'original', max: 'original', minRange: 50 }
                },
                pan: {
                  enabled: true,
                  mode: 'xy',
                },
                zoom: {
                  wheel: {
                    enabled: true,
                  },
                  mode: 'xy',
                },
              },
              legend: {
                display: false,
              },
              tooltip: {
                callbacks: {
                  label: function (ctx) {
                    let label = ctx.dataset.labels[ctx.dataIndex];
                    label += " (" + ctx.parsed.x + ", " + ctx.parsed.y + ")";
                    return label
                  }
                }
              }
            },
            parsing: {
              xAxisKey: xAxisKey,
              yAxisKey: yAxisKey
            },
            onClick: (evt) => {
              var activePoints = evt.chart.getActiveElements(evt);

              if (activePoints[0]) {
                activePoint = $scope.data[activePoints[0]["index"]]
                window.location.href = '/app/#/' + $scope.inventory_type + '/' + activePoint["id"];
              }
            },
            onHover: (evt) => {
              var activePoints = evt.chart.getActiveElements(evt);
              onHover(activePoints);
            },
          },
        });
      }

      function hoverOnAllCharts(activePoints) {
        if (activePoints[0]) {
          var index = activePoints[0]["index"]
          for (const [chartName, chart] of Object.entries(charts)) {
            chart.setActiveElements([
              {
                datasetIndex: 0,
                index: index,
              }
            ])
            chart.update()
          }
        } else {
          for (const [chartName, chart] of Object.entries(charts)) {
            chart.setActiveElements([]);
            chart.update()
          }
        }
      }

      charts = {
        myChart1: createChart(
          elementId = "myChart1",
          xAxisKey = 'site_eui_56',
          yAxisKey = 'gross_floor_area_36',
          onHover = hoverOnAllCharts,
        ),
        myChart2: createChart(
          elementId = "myChart2",
          xAxisKey = 'id',
          yAxisKey = 'gross_floor_area_36',
          onHover = hoverOnAllCharts,
        ),
      }

      $scope.update_charts = function () {
        spinner_utility.show();
        fetch().then(function (data) {
          if (data.status === 'error') {
            let message = data.message;
            Notification.error({ message, delay: 15000 });
            spinner_utility.hide();
            return;
          }

          $scope.data = data.results
          populate_charts(data.results);
          spinner_utility.hide();
        });
      };

      var populate_charts = function (data) {
        labels = data.map(property => property["property_name_22"]);

        for (const [chartName, chart] of Object.entries(charts)) {
          chart.data.datasets[0].data = data
          chart.data.datasets[0].labels = labels
          chart.update();
        }
      }

      var fetch = function () {
        var fn;
        if ($scope.inventory_type === 'properties') {
          fn = inventory_service.get_properties;
        } else if ($scope.inventory_type === 'taxlots') {
          fn = inventory_service.get_taxlots;
        }

        return fn(
          page = 1,
          per_page = undefined,
          cycle = $scope.cycle.selected_cycle,
          include_related = false
        ).then(function (data) {
          return data;
        });
      };

      $scope.update_cycle = function (cycle) {
        inventory_service.save_last_cycle(cycle.id);
        $scope.cycle.selected_cycle = cycle;
        $scope.update_charts();
      };

      $scope.update_charts();
    }
  ]);
