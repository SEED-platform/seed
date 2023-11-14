/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_summary', []).controller('inventory_summary_controller', [
  '$scope',
  '$stateParams',
  '$uibModal',
  'urls',
  'analyses_service',
  'inventory_service',
  'cycles',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, $uibModal, urls, analyses_service, inventory_service, cycles_payload) {
    $scope.inventory_type = $stateParams.inventory_type;

    const lastCycleId = inventory_service.get_last_cycle();
    $scope.cycle = {
      selected_cycle: _.find(cycles_payload.cycles, { id: lastCycleId }) || _.first(cycles_payload.cycles),
      cycles: cycles_payload.cycles
    };

    const refresh_data = () => {
      $scope.progress = {};
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/inventory_loading_modal.html`,
        backdrop: 'static',
        windowClass: 'inventory-progress-modal',
        scope: $scope
      });

      analyses_service.get_summary($scope.cycle.selected_cycle.id).then((data) => {
        $scope.summary_data = data;
        $scope.table_data = [
          {
            text: 'Total Records',
            count: data.total_records
          },
          {
            text: 'Number of Extra Data Fields',
            count: data.number_extra_data_fields
          }
        ];

        const column_settings_count = data['column_settings fields and counts'];
        $scope.column_settings_count = Object.entries(column_settings_count).map(([key, value]) => ({
          column_settings: key,
          count: value
        }));

        modalInstance.close();
      });
    };

    $scope.update_cycle = (cycle) => {
      inventory_service.save_last_cycle(cycle.id);
      $scope.cycle.selected_cycle = cycle;
      refresh_data();
    };

    // load initial data
    refresh_data();
  }
]);
