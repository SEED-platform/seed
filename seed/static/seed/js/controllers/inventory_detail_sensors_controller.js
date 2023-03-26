/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_sensors', [])
  .controller('inventory_detail_sensors_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    '$window',
    'cycles',
    'dataset_service',
    'inventory_service',
    'inventory_payload',
    'sensors',
    'data_loggers',
    'sensor_service',
    'property_sensor_usage',
    'spinner_utility',
    'urls',
    'organization_payload',
    function (
      $scope,
      $stateParams,
      $uibModal,
      $window,
      cycles,
      dataset_service,
      inventory_service,
      inventory_payload,
      sensors,
      data_loggers,
      sensor_service,
      property_sensor_usage,
      spinner_utility,
      urls,
      organization_payload
    ) {
      spinner_utility.show();
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = organization_payload.organization;
      $scope.property_sensor_usage = property_sensor_usage;
      $scope.usage_pagination = property_sensor_usage.pagination;
      $scope.filler_cycle = cycles.cycles[0].id;
      $scope.showOnlyOccupiedReadings = false;

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      var getSensorLabel = function (sensor) {
        return sensor.display_name + " (" + sensor.data_logger + ")";
      };

      var resetSelections = function () {
        $scope.data_logger_selections = _.map(sorted_data_loggers, function (data_logger) {
          return {
            selected: true,
            label: data_logger.display_name,
            value: data_logger.id
          };
        });

        var sensorTypes = new Set(_.map(sorted_sensors, s => s.type))
        $scope.sensor_type_selections = [...sensorTypes].map(t => {
          return {
            selected: true,
            label: t,
            value: t
          };
        })
      };

      // On page load, all sensors and readings
      $scope.has_sensor_readings = $scope.property_sensor_usage.readings.length > 0;
      $scope.has_sensors = sensors.length > 0;
      $scope.has_data_loggers = data_loggers.length > 0;

      var sorted_data_loggers = _.sortBy(data_loggers, ['id']);
      resetSelections();

      var sorted_sensors = _.sortBy(sensors, ['id']);
      resetSelections();

      $scope.data_logger_selection_toggled = function (is_open) {
        if (!is_open) {
          $scope.applyFilters();
        }
      };

      $scope.sensor_type_selection_toggled = function (is_open) {
        if (!is_open) {
          $scope.applyFilters();
        }
      };

      var base_data_logger_col_defs = [{
          field: 'display_name',
          enableHiding: false,
          type: 'string'
        }, {
          field: 'identifier',
          displayName: 'Datalogger ID',
          enableHiding: false
        },{
          field: 'location_description',
          displayName: 'Location Description',
          enableHiding: false
        },{
          field: 'manufacturer_name',
          displayName: 'Manufacturer Name',
          enableHiding: false
        },{
          field: 'model_name',
          displayName: 'Model Name',
          enableHiding: false
        },{
          field: 'serial_number',
          displayName: 'Serial Number',
          enableHiding: false
        }, {
          name: 'actions',
          field: 'actions',
          displayName: 'Actions',
          enableHiding: false,
          cellTemplate: '<div style="display: flex; justify-content: space-around; align-content: center">' +
            '<button type="button" class="btn-primary" style="border-radius: 4px;" ng-click="grid.appScope.open_sensors_upload_modal(row.entity)" translate>UPLOAD_SENSORS_BUTTON</button>' +
            '<button type="button" class="btn-primary" style="border-radius: 4px;" ng-click="grid.appScope.open_sensor_readings_upload_modal(row.entity)" translate>UPLOAD_SENSOR_READINGS_BUTTON</button>' +
            '</div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: false,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: 300
      }];

      var base_sensor_col_defs = [{
          field: 'display_name',
          enableHiding: false,
          type: 'string'
        },{
          field: 'data_logger',
          displayName: 'Data Logger',
          enableHiding: false
        }, {
          field: 'type',
          enableHiding: false
        }, {
          field: 'location_description',
          displayName: 'Location Description',
          enableHiding: false
        },{
          field: 'units',
          enableHiding: false
        }, {
          field: 'column_name',
          enableHiding: false
        },{
          field: 'description',
          enableHiding: false
      }];

      $scope.dataloggerGridOptions = {
        data: sorted_data_loggers,
        columnDefs: base_data_logger_col_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
        minRowsToShow: Math.min(data_loggers.length, 10),
      };

      $scope.sensorGridOptions = {
        data: sensors,
        columnDefs: base_sensor_col_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
        exporterCsvFilename: window.BE.initial_org_name + ($scope.inventory_type === 'taxlots' ? ' Tax Lot ' : ' Property ') + 'sensors.csv',
        enableGridMenu: true,
        exporterMenuPdf: false,
        exporterMenuExcel: false,
        minRowsToShow: Math.min(sensors.length, 10),
      };

      $scope.usageGridOptions = {
        data: $scope.property_sensor_usage.readings,
        columnDefs: $scope.property_sensor_usage.column_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
        exporterCsvFilename: window.BE.initial_org_name + ($scope.inventory_type === 'taxlots' ? ' Tax Lot ' : ' Property ') + 'sensor readings.csv',
        enableGridMenu: true,
        exporterMenuPdf: false,
        exporterMenuExcel: false,
        enableFiltering: false,
        minRowsToShow: Math.min($scope.property_sensor_usage.readings.length, 10),
      };

      $scope.apply_column_settings = function () {
        _.forEach($scope.usageGridOptions.columnDefs, function (column) {
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

      $scope.toggled_show_only_occupied_reading = function (b) {
        $scope.showOnlyOccupiedReadings = b
        $scope.refresh_readings(1, $scope.usage_pagination.per_page);
      };

      // given a list of sensor labels, it returns the filtered readings and column defs
      // This is used by the primary filterBy... functions
      var filterBySensorLabels = function filterBySensorLabels (readings, columnDefs, sensorLabels) {
        var timeColumns = ['timestamp', 'month', 'year'];
        var selectedColumns = sensorLabels.concat(timeColumns);
        var filteredReadings = readings.map(function (reading) {
          return Object.entries(reading).reduce(function (newReading, _ref) {
            var key = _ref[0],
              value = _ref[1];

            if (selectedColumns.includes(key)) {
              newReading[key] = value;
            }

            return newReading;
          }, {});
        });

        var filteredColumnDefs = columnDefs.filter(function (columnDef) {
          return selectedColumns.includes(columnDef.field);
        });
        return {
          readings: filteredReadings,
          columnDefs: filteredColumnDefs
        };
      };

      // given the sensor selections, it returns the filtered readings and column defs
      var filterBySensorSelections = function (readings, columnDefs, dataLoggerSelections, sensor_type_selections) {
        var selectedDataLoggerDisplayNames = dataLoggerSelections.filter((dl) => dl.selected).map((dl) => dl.label);
        var selectedSensorType = sensor_type_selections.filter((t) => t.selected).map((t) => t.label);

        // filter according to sensor selections
        var selectedSensorLabels = sensors.filter(function (sensor) {
          return selectedDataLoggerDisplayNames.includes(sensor.data_logger) & selectedSensorType.includes(sensor.type)
        })
          .map(function (sensor) {
            return getSensorLabel(sensor);
          });

        return filterBySensorLabels(readings, columnDefs, selectedSensorLabels);
      };

      // filters the sensor readings by selected sensors and updates the table
      $scope.applyFilters = function () {
        const results = filterBySensorSelections(
          $scope.property_sensor_usage.readings,
          $scope.property_sensor_usage.column_defs,
          $scope.data_logger_selections,
          $scope.sensor_type_selections
        );
        const readings = results.readings;
        const columnDefs = results.columnDefs;

        $scope.usageGridOptions.columnDefs = columnDefs;
        $scope.usageGridOptions.data = readings;
        $scope.has_sensor_readings = readings.length > 0;
        $scope.apply_column_settings();
      };

      // refresh_readings make an API call to refresh the base readings data
      // according to the selected interval
      $scope.refresh_readings = function (page, per_page) {
        spinner_utility.show();
        sensor_service.property_sensor_usage(
          $scope.inventory.view_id,
          $scope.organization.id,
          $scope.interval.selected,
          $scope.showOnlyOccupiedReadings,
          [], // Not excluding any sensors from the query
          page,
          per_page,
        ).then(function (usage) {
          // update the base data and reset filters
          $scope.property_sensor_usage = usage;
          $scope.usage_pagination = usage.pagination;

          $scope.applyFilters();
          spinner_utility.hide();
        });
      };

      $scope.open_data_logger_upload_modal = function (data_logger) {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/data_logger_upload_modal.html',
          controller: 'data_logger_upload_modal_controller',
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
            sensor_service: sensor_service,
          }
        });
      };

      $scope.open_sensors_upload_modal = function (data_logger) {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/sensors_upload_modal.html',
          controller: 'sensors_upload_modal_controller',
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
            },
            data_logger: function () {
              return data_logger?? {
                  display_name: null,
                  location_description: "",
                  id: null,
              };
            },
            sensor_service: sensor_service,
          }
        });
      };

      $scope.open_sensor_readings_upload_modal = function (data_logger) {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/sensor_readings_upload_modal.html',
          controller: 'sensor_readings_upload_modal_controller',
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
            },
            data_logger_id: function () {
              return data_logger.id
            }
          }
        });
      };

      $scope.inventory_display_name = function (property_type) {
        let error = '';
        let field = property_type == 'property' ? $scope.organization.property_display_field : $scope.organization.taxlot_display_field;
        if (!(field in $scope.item_state)) {
          error = field + ' does not exist';
          field = 'address_line_1';
        }
        if (!$scope.item_state[field]) {
          error += (error == '' ? '' : ' and default ') + field + ' is blank';
        }
        $scope.inventory_name = $scope.item_state[field] ? $scope.item_state[field] : '(' + error + ') <i class="glyphicon glyphicon-question-sign" title="This can be changed from the organization settings page."></i>';
      };
    }]);
