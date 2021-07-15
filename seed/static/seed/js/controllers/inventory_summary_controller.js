/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_summary', [])
  .controller('inventory_summary_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'analyses_service',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      analyses_service,
      cycles,
    ) {
      $scope.inventory_type = $stateParams.inventory_type;

      const lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: _.find(cycles.cycles, {id: lastCycleId}) || _.first(cycles.cycles),
        cycles: cycles.cycles
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
          .then(data, function(data) {
            console.log('Summary data:', data)
            $scope.summary_data = data
            // TODO: update the chart (help: https://stackoverflow.com/questions/20905429/update-dimple-js-chart-when-select-a-new-option)
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
