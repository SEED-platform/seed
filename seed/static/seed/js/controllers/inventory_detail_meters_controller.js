/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.inventory_detail_meters', []).controller('inventory_detail_meters_controller', [
  '$state',
  '$scope',
  '$stateParams',
  '$uibModal',
  '$window',
  'meter_service',
  'organization_service',
  'cycles',
  'dataset_service',
  'inventory_service',
  'inventory_group_service',
  'inventory_payload',
  'meters',
  'property_meter_usage',
  'spinner_utility',
  'urls',
  'organization_payload',
  // eslint-disable-next-line func-names
  function (
    $state,
    $scope,
    $stateParams,
    $uibModal,
    $window,
    meter_service,
    organization_service,
    cycles,
    dataset_service,
    inventory_service,
    inventory_group_service,
    inventory_payload,
    meters,
    property_meter_usage,
    spinner_utility,
    urls,
    organization_payload
  ) {
    spinner_utility.show();
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.item_state = inventory_payload.state;

    inventory_group_service.get_groups_for_inventory('properties', [inventory_payload.property.id]).then((groups) => {
      $scope.groups = groups;
    });

    $scope.organization = organization_payload.organization;
    $scope.filler_cycle = cycles.cycles[0].id;

    $scope.inventory = {
      view_id: $stateParams.view_id
    };

    const getMeterLabel = ({ source, source_id, type }) => `${type} - ${source} - ${source_id ?? 'None'}`;

    const resetSelections = () => {
      $scope.sorted_meters = _.sortBy(meters, ['source', 'source_id', 'type']);
    };

    // On page load, all meters and readings
    $scope.has_meters = meters.length > 0;
    $scope.data = property_meter_usage.readings;
    $scope.has_readings = $scope.data.length > 0;

    resetSelections();

    // dont show edit if disabled?
    const buttons = (
      '<div class="meters-table-actions" style="display: flex; flex-direction=column">' +
      ' <button type="button" ng-show="grid.appScope.menu.user.organization.user_role !== \'viewer\' && grid.appScope.groups.length" class="btn-primary" style="border-radius: 4px;" ng-click="grid.appScope.open_meter_connection_edit_modal(row.entity)" title="Edit Meter Connection"><i class="fa-solid fa-pencil"></i></button>' +
      // ' <button type="button" ng-show="grid.appScope.menu.user.organization.user_role !== \'viewer\' && !grid.appScope.groups.length" class="btn-gray" style="border-radius: 4px;" ng-click="grid.appScope.open_meter_connection_edit_modal(row.entity)" title="To Edit Connection, a meter must be part of an inventory group" ng-disabled="true"><i class="fa-solid fa-pencil"></i></button>' +
      ' <button type="button" ng-show="grid.appScope.menu.user.organization.user_role !== \'viewer\'" class="btn-danger" style="border-radius: 4px;" ng-click="grid.appScope.open_meter_deletion_modal(row.entity)" title="Delete Meter"><i class="fa-solid fa-xmark"></i></button>' +
      '</div>'
    );

    $scope.serviceLink = (entity) => {
      if (entity.service_name === null) return;
      return `<a id="inventory-summary" ui-sref="inventory_list(::{inventory_type: inventory_type})" ui-sref-active="active">${entity.service_name}</a>`;
    };

    $scope.meterGridOptions = {
      data: 'sorted_meters',
      columnDefs: [
        { field: 'id' },
        { field: 'type' },
        { field: 'alias' },
        { field: 'source' },
        { field: 'source_id' },
        { field: 'scenario_id' },
        { field: 'connection_type' },
        { field: 'service_name', displayName: 'Connection', cellTemplate: '<a id="inventory-summary" ui-sref="inventory_group_detail_systems(::{inventory_type: grid.appScope.inventory_type, group_id: row.entity.service_group})" ui-sref-active="active">{$ row.entity.service_name $}</a>' },
        { field: 'is_virtual' },
        { field: 'scenario_name' },
        { field: 'actions', cellTemplate: buttons }
      ],
      enableGridMenu: true,
      enableSelectAll: true,
      exporterMenuPdf: false,
      exporterMenuExcel: false,
      exporterCsvFilename: () => `${$scope.inventory_display_name ? $scope.inventory_display_name : $stateParams.view_id}_meters.csv`,
      enableColumnResizing: true,
      flatEntityAccess: true,
      fastWatch: true,
      gridMenuShowHideColumns: false,
      rowIdentity: (meter) => meter.id,
      minRowsToShow: Math.min($scope.sorted_meters.length, 10),
      onRegisterApi(meterGridApi) {
        $scope.meterGridApi = meterGridApi;

        _.delay($scope.updateHeight, 150);

        const debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
        angular.element($window).on('resize', debouncedHeightUpdate);
        $scope.$on('$destroy', () => {
          angular.element($window).off('resize', debouncedHeightUpdate);
        });

        $scope.meterGridApi.selection.on.rowSelectionChanged($scope, $scope.applyFilters);
        $scope.meterGridApi.selection.on.rowSelectionChangedBatch($scope, $scope.applyFilters);

        // only run once, once data is ready, TODO: find a better way to do this.
        let init = true;
        $scope.meterGridApi.core.on.rowsRendered($scope, () => {
          if (init) {
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
      exporterCsvFilename: () => `${$scope.inventory_dispaly_name ? $scope.inventory_dispaly_name : $stateParams.view_id}_meter_readings.csv`,
      enableColumnResizing: true,
      enableFiltering: true,
      flatEntityAccess: true,
      fastWatch: true,
      gridMenuShowHideColumns: false,
      minRowsToShow: Math.min($scope.data.length, 15),
      onRegisterApi(readingGridApi) {
        $scope.readingGridApi = readingGridApi;

        _.delay($scope.updateHeight, 150);

        const debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
        angular.element($window).on('resize', debouncedHeightUpdate);
        $scope.$on('$destroy', () => {
          angular.element($window).off('resize', debouncedHeightUpdate);
        });
      }
    };

    $scope.open_meter_deletion_modal = (meter) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/meter_deletion_modal.html`,
        controller: 'meter_deletion_modal_controller',
        resolve: {
          organization_id: () => $scope.organization.id,
          group_id: () => null,
          meter: () => meter,
          view_id: () => $scope.inventory.view_id,
          refresh_meters_and_readings: () => $scope.refresh_meters_and_readings
        }
      });
    };

    $scope.open_meter_connection_edit_modal = (meter) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/meter_edit_modal.html`,
        controller: 'meter_edit_modal_controller',
        resolve: {
          organization_id: () => $scope.organization.id,
          meter: () => meter,
          property_id: () => inventory_payload.property.id,
          system_id: () => null,
          view_id: () => $scope.inventory.view_id,
          refresh_meters_and_readings: () => $scope.refresh_meters_and_readings
        }
      });
    };

    $scope.apply_column_settings = () => {
      _.forEach($scope.meterReadGridOptions.columnDefs, (column) => {
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
      options: ['Exact', 'Month', 'Year'],
      selected: 'Exact'
    };

    // given a list of meter labels, it returns the filtered readings and column defs
    // This is used by the primary filterBy... functions
    const filterByMeterLabels = (readings, columnDefs, meterLabels) => {
      const timeColumns = ['start_time', 'end_time', 'month', 'year'];
      const selectedColumns = meterLabels.concat(timeColumns);
      const filteredReadings = readings.filter((reading) => meterLabels.some((label) => Object.keys(reading).includes(label)));
      const filteredColumnDefs = columnDefs.filter((columnDef) => selectedColumns.includes(columnDef.field));
      return {
        readings: filteredReadings,
        columnDefs: filteredColumnDefs
      };
    };

    // given the meter selections, it returns the filtered readings and column defs
    const filterByMeterSelections = (readings, columnDefs) => {
      // filter according to meter selections
      const selected_meters = $scope.meterGridApi.selection.getSelectedGridRows();
      const selectedMeterLabels = selected_meters.map((row) => getMeterLabel(row.entity));

      return filterByMeterLabels(readings, columnDefs, selectedMeterLabels);
    };

    // filters the meter readings by selected meters and updates the table
    $scope.applyFilters = () => {
      const results = filterByMeterSelections(property_meter_usage.readings, property_meter_usage.column_defs);
      $scope.data = results.readings;
      $scope.meterReadGridOptions.columnDefs = results.columnDefs;
      $scope.has_meters = meters.length > 0;
      $scope.has_readings = $scope.data.length > 0;
      $scope.apply_column_settings();
    };

    // refresh_readings make an API call to refresh the base readings data
    // according to the selected interval
    $scope.refresh_meters_and_readings = () => {
      // Any reason we can't just reload? Solves issues with null group_ids
      $state.reload();
    };

    // refresh_readings make an API call to refresh the base readings data
    // according to the selected interval
    $scope.refresh_readings = () => {
      spinner_utility.show();
      meter_service
        .property_meter_usage(
          $scope.inventory.view_id,
          $scope.organization.id,
          $scope.interval.selected,
          [] // Not excluding any meters from the query
        )
        .then((usage) => {
          // update the base data and reset filters
          property_meter_usage = usage;

          resetSelections();
          $scope.applyFilters();
          spinner_utility.hide();
        });
    };

    $scope.open_green_button_upload_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/green_button_upload_modal.html`,
        controller: 'green_button_upload_modal_controller',
        resolve: {
          filler_cycle: () => $scope.filler_cycle,
          organization_id: () => $scope.organization.id,
          view_id: () => $scope.inventory.view_id,
          system_id: () => null,
          datasets: () => dataset_service.get_datasets().then((result) => result.datasets)
        }
      });
    };

    $scope.inventory_display_name = organization_service.get_inventory_display_value($scope.organization, $scope.inventory_type === 'properties' ? 'property' : 'taxlot', $scope.item_state);

    $scope.updateHeight = () => {
      let height = 0;
      _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls'], (selector) => {
        const element = angular.element(selector)[0];
        if (element) height += element.offsetHeight;
      });
      angular.element('#grid-container').css('height', `calc(100vh - ${height + 2}px)`);
      angular.element('#grid-container > div').css('height', `calc(100vh - ${height + 4}px)`);
      $scope.readingGridApi.core.handleWindowResize();
      $scope.meterGridApi.core.handleWindowResize();
    };
  }
]);
