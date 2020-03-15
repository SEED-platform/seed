angular.module('BE.seed.controller.inventory_detail_meters', [])
  .controller('inventory_detail_meters_controller', [
    '$state',
    '$scope',
    '$stateParams',
    '$uibModal',
    '$window',
    'meter_service',
    'cycles',
    'dataset_service',
    'inventory_service',
    'inventory_payload',
    'meters',
    'property_meter_usage',
    'spinner_utility',
    'urls',
    'user_service',
    function (
      $state,
      $scope,
      $stateParams,
      $uibModal,
      $window,
      meter_service,
      cycles,
      dataset_service,
      inventory_service,
      inventory_payload,
      meters,
      property_meter_usage,
      spinner_utility,
      urls,
      user_service
    ) {
      spinner_utility.show();

      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = user_service.get_organization();
      $scope.filler_cycle = cycles.cycles[0].id;

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      // On page load, all meters and readings
      $scope.excluded_meter_ids = [];
      $scope.data = property_meter_usage.readings;
      $scope.has_readings = $scope.data.length > 0;

      var sorted_meters = _.sortBy(meters, ['source', 'source_id', 'type']);
      $scope.meter_selections = _.map(sorted_meters, function (meter) {
        return {
          selected: true,
          label: meter.type + ' - ' + meter.source + ' - ' + meter.source_id,
          value: meter.id
        };
      });
      $scope.has_meters = $scope.meter_selections.length > 0;

      $scope.meter_selection_toggled = function (is_open) {
        if (!is_open) {
          var updated_selections = _.map(_.filter($scope.meter_selections, ['selected', false]), 'value');
          if (!_.isEqual($scope.excluded_meter_ids, updated_selections)) {
            $scope.excluded_meter_ids = updated_selections;
            $scope.refresh_readings();
          }
        }
      };

      $scope.gridOptions = {
        data: 'data',
        columnDefs: property_meter_usage.column_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });
        }
      };

      $scope.apply_column_settings = function () {
        _.forEach($scope.gridOptions.columnDefs, function (column) {
          column.enableHiding = false;
          column.enableColumnResizing = true;

          if (column.field === 'year') {
            // Filter years like integers
            column.filter = inventory_service.combinedFilter();
          } else if (column._filter_type === 'reading') {
            column.cellFilter = 'number: 2';
            column.filter = inventory_service.combinedFilter();
          } else if (column._filter_type === 'datetime') {
            column.filter = inventory_service.dateFilter();
          }
        });
      };

      $scope.apply_column_settings();

      // Ideally, these should be translatable, but the "selected" property
      // should always be in English as this gets sent to BE.
      $scope.interval = {
        options: [
          'Exact',
          'Month',
          'Year'
        ],
        selected: 'Exact'
      };

      $scope.refresh_readings = function () {
        spinner_utility.show();
        meter_service.property_meter_usage(
          $scope.inventory.view_id,
          $scope.organization.id,
          $scope.interval.selected,
          $scope.excluded_meter_ids
        ).then(function (usage) {
          $scope.data = usage.readings;
          $scope.gridOptions.columnDefs = usage.column_defs;
          $scope.has_readings = $scope.data.length > 0;
          $scope.apply_column_settings();
          spinner_utility.hide();
        });
      };

      $scope.open_green_button_upload_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/green_button_upload_modal.html',
          controller: 'green_button_upload_modal_controller',
          resolve: {
            filler_cycle: function () {
              return $scope.filler_cycle;
            },
            organization_id: function () {
              return $scope.organization.id;
            },
            view_id: function () {
              return $scope.inventory.view_id;
            },
            datasets: function () {
              return dataset_service.get_datasets().then(function (result) {
                return result.datasets;
              });
            }
          }
        });
      };

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.gridApi.core.handleWindowResize();
      };
    }]);
