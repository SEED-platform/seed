/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
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
    'organization_payload',
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
      user_service,
      organization_payload
    ) {
      spinner_utility.show();
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = organization_payload.organization;
      $scope.filler_cycle = cycles.cycles[0].id;

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      var getMeterLabel = function (meter) {
        return meter.type + ' - ' + meter.source + ' - ' + meter.source_id;
      };

      var resetSelections = function () {
        $scope.sorted_meters = _.sortBy(meters, ['source', 'source_id', 'type']);
      };

      // On page load, all meters and readings
      $scope.has_meters = meters.length > 0;
      $scope.data = property_meter_usage.readings;
      $scope.has_readings = $scope.data.length > 0;

      resetSelections();

      deleteButton = '<button type="button" class="btn-primary" style="border-radius: 4px;" ng-click="grid.appScope.open_meter_deletion_modal(row.entity)" translate>Delete</button>';

      $scope.meterGridOptions = {
        data: 'sorted_meters',
        columnDefs: [
          {field: "type"},
          {field: "alias"},
          {field: "source"},
          {field: "source_id"},
          {field: "scenario_id"},
          {field: "is_virtual"},
          {field: "scenario_name"},
          {field: "actions", cellTemplate: deleteButton},
        ],
        enableGridMenu: true,
        enableSelectAll: true,
        exporterMenuPdf: false,
        exporterMenuExcel: false,
        exporterCsvFilename: () => `${$scope.inventory_name ? $scope.inventory_name : $stateParams.view_id} meter.csv`,
        enableColumnResizing: true,
        flatEntityAccess: true,
        fastWatch: true,
        gridMenuShowHideColumns: false,
        rowIdentity: (meter) => {return meter.id},
        minRowsToShow: Math.min($scope.sorted_meters.length, 10),
        onRegisterApi: function (meterGridApi) {
          $scope.meterGridApi = meterGridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });

          $scope.meterGridApi.selection.on.rowSelectionChanged($scope, $scope.applyFilters);
          $scope.meterGridApi.selection.on.rowSelectionChangedBatch($scope, $scope.applyFilters);

          // only run once, once data is ready, TODO: find a better way to do this.
          init = true;
          $scope.meterGridApi.core.on.rowsRendered($scope, function() {
            if(init){
              $scope.meterGridApi.selection.selectAllRows();
              init = false;
            }
          });
        }
      };

      $scope.meterReadGridOptions = {
        data: 'data',
        columnDefs: property_meter_usage.column_defs,
        enableGridMenu: true,
        enableSelectAll: true,
        exporterMenuPdf: false,
        exporterMenuExcel: false,
        exporterCsvFilename: () => `${$scope.inventory_name ? $scope.inventory_name : $stateParams.view_id} meter_readings.csv`,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
        gridMenuShowHideColumns: false,
        minRowsToShow: Math.min($scope.data.length, 15),
        onRegisterApi: function (readingGridApi) {
          $scope.readingGridApi = readingGridApi;

          _.delay($scope.updateHeight, 150);

          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });
        }
      };

      $scope.open_meter_deletion_modal = function (meter) {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/meter_deletion_modal.html',
          controller: 'meter_deletion_modal_controller',
          resolve: {
            meter: function () {
              return meter;
            },
            view_id: function () {
              return $scope.inventory.view_id;
            },
            refresh_meters_and_readings: function () {
              return $scope.refresh_meters_and_readings;
            },
          }
        });
      };

      $scope.apply_column_settings = function () {
        _.forEach($scope.meterReadGridOptions.columnDefs, function (column) {
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

      // given a list of meter labels, it returns the filtered readings and column defs
      // This is used by the primary filterBy... functions
      var filterByMeterLabels = function filterByMeterLabels (readings, columnDefs, meterLabels) {
        var timeColumns = ['start_time', 'end_time', 'month', 'year'];
        var selectedColumns = meterLabels.concat(timeColumns);
        var filteredReadings = readings.filter(reading => {
          return meterLabels.some(label => Object.keys(reading).includes(label));
        });
        var filteredColumnDefs = columnDefs.filter(function (columnDef) {
          return selectedColumns.includes(columnDef.field);
        });
        return {
          readings: filteredReadings,
          columnDefs: filteredColumnDefs
        };
      };

      // given the meter selections, it returns the filtered readings and column defs
      var filterByMeterSelections = function (readings, columnDefs) {
        // filter according to meter selections
        var selected_meters = $scope.meterGridApi.selection.getSelectedGridRows()
        var selectedMeterLabels = selected_meters.map(function (row) {
            return getMeterLabel(row.entity);
          });

        return filterByMeterLabels(readings, columnDefs, selectedMeterLabels);
      };

      // filters the meter readings by selected meters and updates the table
      $scope.applyFilters = function () {
        results = filterByMeterSelections(property_meter_usage.readings, property_meter_usage.column_defs);
        $scope.data = results.readings;
        $scope.meterReadGridOptions.columnDefs = results.columnDefs;;
        $scope.has_meters = meters.length > 0;
        $scope.has_readings = $scope.data.length > 0;
        $scope.apply_column_settings();
      };

      // refresh_readings make an API call to refresh the base readings data
      // according to the selected interval
      $scope.refresh_meters_and_readings = function () {
        spinner_utility.show();
        get_meters_Promise = meter_service.get_meters(
          $scope.inventory.view_id,
          $scope.organization.id,
        )
        get_readings_Promise = meter_service.property_meter_usage(
          $scope.inventory.view_id,
          $scope.organization.id,
          $scope.interval.selected,
          [] // Not excluding any meters from the query
        )
        Promise.all([get_meters_Promise, get_readings_Promise]).then(function (data) {
          // update the base data and reset filters
          [meters, property_meter_usage] = data;

          resetSelections();
          $scope.applyFilters();
          spinner_utility.hide();
        });
      };

      // refresh_readings make an API call to refresh the base readings data
      // according to the selected interval
      $scope.refresh_readings = function () {
        spinner_utility.show();
        meter_service.property_meter_usage(
          $scope.inventory.view_id,
          $scope.organization.id,
          $scope.interval.selected,
          [] // Not excluding any meters from the query
        ).then(function (usage) {
          // update the base data and reset filters
          property_meter_usage = usage;

          resetSelections();
          $scope.applyFilters();
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

      const get_inventory_display_name = function (property_type) {
        let error = '';
        let field = property_type === 'property' ? $scope.organization.property_display_field : $scope.organization.taxlot_display_field;
        if (!(field in $scope.item_state)) {
          error = `${field} does not exist`;
          field = 'address_line_1';
        }
        if (!$scope.item_state[field]) {
          error += `${error === '' ? '' : ' and default '}${field} is blank`;
        }
        $scope.inventory_name_error = error;
        $scope.inventory_name = $scope.item_state[field] ? $scope.item_state[field] : '';
      };

      $scope.updateHeight = function () {
        let height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.readingGridApi.core.handleWindowResize();
        $scope.meterGridApi.core.handleWindowResize();
      };

      get_inventory_display_name($scope.inventory_type === 'properties' ? 'property' : 'taxlot');
    }]);
