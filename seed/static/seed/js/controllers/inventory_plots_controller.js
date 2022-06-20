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
        selected_cycle: _.find(cycles.cycles, {id: lastCycleId}) || _.first(cycles.cycles),
        cycles: cycles.cycles
      };

      var canvas = document.getElementById("myChart");
      var ctx = canvas.getContext("2d");
      var myChart = new Chart(ctx, {
        type: 'scatter',
        data: {
          datasets: [{
            data: [],
            backgroundColor: "rgba(0,255,255,0.7)",
          }],
        },
        options: {
          plugins: {
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
        },
      });

      canvas.onclick = function (evt) {
        var activePoints = myChart.getActiveElements(evt);

        if (activePoints[0]) {
          activePoint = $scope.data[activePoints[0]["index"]]
          console.log(activePoint);
          window.location.href = '/app/#/' + $scope.inventory_type + '/' + activePoint["id"];
        }
      };

      $scope.update_chart = function () {
        spinner_utility.show();
        fetch().then(function (data) {
          if (data.status === 'error') {
            let message = data.message;
            Notification.error({ message, delay: 15000 });
            spinner_utility.hide();
            return;
          }

          $scope.data = data.results
          populate_chart(data.results);
          spinner_utility.hide();
        });
      };

      var populate_chart = function (data) {
        labels = []
        chart_data = []

        data.forEach(property => {
          chart_data.push({
            "x": property["total_ghg_emissions_intensity_71"],
            "y": property["site_eui_56"]
          })
          labels.push(property["pm_property_id_1"])
        });

        myChart.data.datasets[0].data = chart_data
        myChart.data.datasets[0].labels = labels
        myChart.update();
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
        ).then(function (data) {
          return data;
        });
      };

      $scope.update_cycle = function (cycle) {
        inventory_service.save_last_cycle(cycle.id);
        $scope.cycle.selected_cycle = cycle;
        $scope.update_chart();
      };

      $scope.update_chart();
    }
  ]);
