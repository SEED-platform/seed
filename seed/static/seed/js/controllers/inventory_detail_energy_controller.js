angular.module('BE.seed.controller.inventory_detail_energy', [])
  .controller('inventory_detail_energy_controller', [
    '$state',
    '$scope',
    '$stateParams',
    '$uibModal',
    'energy_service',
    'cycles',
    'inventory_service',
    'property_energy_usage',
    'spinner_utility',
    'urls',
    'user_service',
    function (
      $state,
      $scope,
      $stateParams,
      $uibModal,
      energy_service,
      cycles,
      inventory_service,
      property_energy_usage,
      spinner_utility,
      urls,
      user_service
    ) {
      spinner_utility.show();

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = user_service.get_organization();
      $scope.filler_cycle = cycles.cycles[0].id;

      $scope.inventory = {
        view_id: $stateParams.view_id,
      };

      $scope.data = property_energy_usage.readings;
      $scope.has_meters = $scope.data.length > 0;

      $scope.gridOptions = {
        data: 'data',
        columnDefs: property_energy_usage.column_defs,
        enableFiltering: true,
      };

      $scope.apply_column_settings = function() {
        _.forEach($scope.gridOptions.columnDefs, function(column) {
          if (column.field == "year") {
            // Filter years like integers
            column.filter = inventory_service.combinedFilter();
          } else if (column._filter_type == "reading") {
            column.cellFilter = "number: 1";
            column.filter = inventory_service.combinedFilter();
          } else if (column._filter_type == "datetime") {
            column.filter = inventory_service.dateFilter();
          }
        });
      };

      $scope.apply_column_settings();

      $scope.interval = {
        options: [ // TODO: Translate this
          'Exact',
          'Month',
          'Year',
        ],
        selected: 'Exact',
      };

      $scope.update_interval = function(selected_interval) {
        spinner_utility.show();
        $scope.interval.selected = selected_interval;
        energy_service.property_energy_usage($scope.inventory.view_id, $scope.organization.id, selected_interval).then(function(usage) {
          $scope.data = usage.readings;
          $scope.gridOptions.columnDefs = usage.column_defs;
          $scope.has_meters = $scope.data.length > 0;
          $scope.apply_column_settings();
          spinner_utility.hide();
        });
      };

      $scope.open_green_button_upload_modal = function () {
        var dataModalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/green_button_upload_modal.html',
          controller: 'green_button_upload_modal_controller',
          resolve: {
            filler_cycle: function() {
              return $scope.filler_cycle;
            },
            organization_id: function() {
              return $scope.organization.id;
            },
            view_id: function () {
              return $scope.inventory.view_id;
            }
          }
        });

        dataModalInstance.result.finally(function () {
          init();
        });
      };
    }]);
