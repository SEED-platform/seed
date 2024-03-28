/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_summary', []).controller('inventory_summary_controller', [
  '$scope',
  '$stateParams',
  '$uibModal',
  '$window',
  'urls',
  'analyses_service',
  'inventory_service',
  'cycles',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, $uibModal, $window, urls, analyses_service, inventory_service, cycles_payload) {
    $scope.inventory_type = $stateParams.inventory_type;

    const lastCycleId = inventory_service.get_last_cycle();
    $scope.cycle = {
      selected_cycle: _.find(cycles_payload.cycles, { id: lastCycleId }) || _.first(cycles_payload.cycles),
      cycles: cycles_payload.cycles
    };

    $scope.summaryGridOptions = {
      data: [],
      columnDefs: [
        { field: 'Summary' },
        { field: 'Count' }
      ],
      onRegisterApi: (gridApi) => {
        $scope.summaryGridOptions = gridApi;
      },
      minRowsToShow: 2
    };

    $scope.countGridOptions = {
      data: [],
      enableSorting: true,
      enableFiltering: true,
      columnDefs: [
        { field: 'Field' },
        { field: 'Count' }
      ],

      onRegisterApi: (gridApi) => {
        $scope.countGridOptions = gridApi;
      }
    };

    $scope.updateHeight = () => {
      let height = 0;
      _.forEach(['.header', '.page_header_container', '.section_nav_container'], (selector) => {
        const element = angular.element(selector)[0];
        if (element) height += element.offsetHeight;
      });
      angular.element('#count-grid').css('height', `calc(100vh - ${height - 1}px)`);
      $scope.countGridOptions.core.handleWindowResize();
    };

    const debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
    angular.element($window).on('resize', debouncedHeightUpdate);
    $scope.$on('$destroy', () => {
      angular.element($window).off('resize', debouncedHeightUpdate);
    });

    _.delay($scope.updateHeight, 150);

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
            Summary: 'Total Records',
            Count: data.total_records
          },
          {
            Summary: 'Number of Extra Data Fields',
            Count: data.number_extra_data_fields
          }
        ];
        $scope.summaryGridOptions.data = $scope.table_data;

        const column_settings_count = data['column_settings fields and counts'];
        $scope.column_settings_count = Object.entries(column_settings_count).map(([key, value]) => ({
          Field: key,
          Count: value
        }));

        $scope.countGridOptions.data = $scope.column_settings_count;
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
