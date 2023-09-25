/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
      $scope.chartsInfo = [
        {
          "chartName": "Year Built vs ECI",
          "xDisplayName": "Year Built",
          "yDisplayName": "ECI"
        },
        {
          "chartName": "CO2 vs Gross Floor Area (ft²)",
          "xDisplayName": "Total GHG Emissions",
          "yDisplayName": "Gross Floor Area (ft²)"
        },
        {
          "chartName": "Better Savings vs ECI",
          "yDisplayName": "BETTER Potential Energy Savings (kWh)",
          "xDisplayName": "ECI"
        },
        {
          "chartName": "CO2/sqft vs Year Built",
          "xDisplayName": "CO2/sqft",
          "yDisplayName": "Year Built"
        },
      ];

      const property_name_column = all_columns.find(c => c["column_name"] == "property_name");
      neededColumns = new Set([property_name_column["id"]]);

      $scope.chartsInfo.forEach(chartInfo => {
        x_column = all_columns.find(c => c["displayName"] == chartInfo["xDisplayName"])
        y_column = all_columns.find(c => c["displayName"] == chartInfo["yDisplayName"])

        if (!!x_column) neededColumns.add(x_column["id"])
        if (!!y_column) neededColumns.add(y_column["id"])

        chartInfo["xName"] = x_column? x_column["name"]: null;
        chartInfo["yName"] = y_column? y_column["name"]: null;
        chartInfo["populated"] = Boolean(!!x_column & !!y_column);
      });

      var createChart = function (elementId, xAxisKey, xDisplayName, yAxisKey, yDisplayName, onHover) {
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
                  text: xDisplayName,
                },
              },
              y: {
                display: true,
                title: {
                  display: true,
                  text: yDisplayName,
                }
              }
            },
            plugins: {
              title: {
                display: true,
                text: elementId
              },
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
          for (const chart of charts) {
            chart.setActiveElements([
              {
                datasetIndex: 0,
                index: index,
              }
            ])
            chart.update()
          }
        } else {
          for (const chart of charts) {
            chart.setActiveElements([]);
            chart.update()
          }
        }
      }

      charts = $scope.chartsInfo.filter(chartInfo => chartInfo["populated"])
        .map(chartInfo => {
          return createChart(
            elementId = chartInfo["chartName"],
            xAxisKey = chartInfo["xName"],
            xAxisName = chartInfo["xDisplayName"],
            yAxisKey = chartInfo["yName"],
            yAxisName = chartInfo["yDisplayName"],
            onHover = hoverOnAllCharts
          )
        })

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
        labels = data.map(property => property[property_name_column["name"]]);

        for (const chart of charts) {
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
          profile_id = null,
          include_view_ids = null,
          exclude_view_ids = null,
          save_last_cycle = true,
          organization_id = null,
          include_related = true,
          column_filters = null,
          column_sorts = null,
          ids_only = null,
          shown_column_ids = Array.from(neededColumns).join() // makes set string, ie {1, 2} -> "1,2"
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
