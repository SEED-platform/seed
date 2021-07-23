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

      const lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: _.find(cycles_payload.cycles, {id: lastCycleId}) || _.first(cycles_payload.cycles),
        cycles: cycles_payload.cycles
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
          .then(function(data) {
            console.log('Summary data:', data)
            originalData = data
            // TODO: update the chart (help: https://stackoverflow.com/questions/20905429/update-dimple-js-chart-when-select-a-new-option)

            // function analysisCtrl($scope) {
              $scope.data = [
                {
                  text: "total_records",
                  count: originalData['total_records']
                },{
                  text: "number_extra_data_fields",
                  count: originalData['number_extra_data_fields']
                }
              ];
            // }

            //function analysisCtrl($scope) {
              //$scope.data = [
                //{
                  //text: "extra_data fields and count",
                  //count: originalData['extra_data fields and count']
                //}
              //];
            //}

            var svg = dimple.newSvg("#chart", 1100, 900);
            var data = originalData['property_types'];

            var chart = new dimple.chart(svg, data);
            var x = chart.addCategoryAxis("x", "extra_data__Largest Property Use Type");
            var y = chart.addMeasureAxis("y", "count");

            chart.addSeries(null, dimple.plot.bar);
            chart.draw();

            var svg = dimple.newSvg("#chart", 1100, 900);
            var data = originalData['year_built'];

            var chart = new dimple.chart(svg, data);
            var x = chart.addCategoryAxis("x", "year_built");
            var y = chart.addMeasureAxis("y", "percentage");

            chart.addSeries(null, dimple.plot.bar);
            chart.draw();

            var svg = dimple.newSvg("#chart", 1100, 900);
            var data = originalData['energy'];

            var chart = new dimple.chart(svg, data);
            var x = chart.addCategoryAxis("x", "site_eui");
            var y = chart.addMeasureAxis("y", "percentage");

            chart.addSeries(null, dimple.plot.bar);
            chart.draw();

            var svg = dimple.newSvg("#chart", 1100, 900);
            var data = originalData['Square Footage'];

            var chart = new dimple.chart(svg, data);
            var x = chart.addCategoryAxis("x", "gross_floor_area");
            var y = chart.addMeasureAxis("y", "percentage");

            chart.addSeries(null, dimple.plot.bar);
            chart.draw();

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
