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
      organization_payload,
    ) {
      spinner_utility.show();
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = organization_payload.organization;
      $scope.property_sensor_usage = property_sensor_usage;
      $scope.filler_cycle = cycles.cycles[0].id;

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      var getSensorLabel = function (sensor) {
        return sensor.display_name + " (" + sensor.data_logger + ")";
      };

      var resetSelections = function () {
        $scope.sensor_selections = _.map(sorted_sensors, function (sensor) {
          return {
            selected: true,
            label: getSensorLabel(sensor),
            value: sensor.id
          };
        });
      };

      $scope.dataloggers = $scope.property_sensor_usage.readings.map(reading => {
          readings = _.omit(reading, "timestamp");
          readings_by_sensor = Object.keys(readings).map(function(key) {
            return {
              sensor: key,
              value: readings[key]
            }
          });
        
          return {
          timestamp: reading["timestamp"],
          readings: readings_by_sensor
        }
      });

      // On page load, all sensors and readings
      $scope.has_sensor_readings = $scope.property_sensor_usage.readings.length > 0;
      $scope.has_sensors = sensors.length > 0;
      $scope.has_data_loggers = data_loggers.length > 0;

      var sorted_data_loggers = _.sortBy(data_loggers, ['id']);
      resetSelections();

      var sorted_sensors = _.sortBy(sensors, ['id']);
      resetSelections();

      $scope.sensor_selection_toggled = function (is_open) {
        if (!is_open) {
          $scope.applyFilters();
        }
      };

      var base_data_logger_col_defs = [{
          field: 'display_name',
          enableHiding: false,
          type: 'string'
        }, {
          field: 'location_identifier',
          displayName: 'location identifier',        
          enableHiding: false
        }, {
          name: 'actions',
          field: 'actions',
          displayName: 'actions',      
          enableHiding: false,
          cellTemplate: '<div style="display: flex; justify-content: center">' +
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
          width: 200
      }];

      var base_sensor_col_defs = [{
          field: 'display_name',
          enableHiding: false,
          type: 'string'
        }, {
          field: 'type',
          enableHiding: false
        }, {
          field: 'location_identifier',
          displayName: 'location identifier',        
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
        },{
          field: 'data_logger',
          displayName: 'Data Logger',
          enableHiding: false
      }];

      $scope.dataloggerGridOptions = {
        data: sorted_data_loggers,
        columnDefs: base_data_logger_col_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
      };

      $scope.sensorGridOptions = {
        data: sensors,
        columnDefs: base_sensor_col_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
      };

      $scope.usageGridOptions = {
        data: $scope.property_sensor_usage.readings,
        columnDefs: $scope.property_sensor_usage.column_defs,
        enableColumnResizing: true,
        enableFiltering: true,
        flatEntityAccess: true,
        fastWatch: true,
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
      var filterBySensorSelections = function (readings, columnDefs, sensorSelections) {
        // filter according to sensor selections
        var selectedSensorLabels = sensorSelections.filter(function (selection) {
          return selection.selected;
        })
          .map(function (selection) {
            return selection.label;
          });
        
        return filterBySensorLabels(readings, columnDefs, selectedSensorLabels);
      };

      // filters the sensor readings by selected sensors and updates the table
      $scope.applyFilters = function () {
        results = filterBySensorSelections(property_sensor_usage.readings, property_sensor_usage.column_defs, $scope.sensor_selections);
        readings = results.readings;
        columnDefs = results.columnDefs;

        $scope.usageGridOptions.columnDefs = columnDefs;
        $scope.usageGridOptions.data = readings;
        $scope.has_sensor_readings = $scope.property_sensor_usage.readings.length > 0;
        $scope.apply_column_settings();
      };

      // refresh_readings make an API call to refresh the base readings data
      // according to the selected interval
      $scope.refresh_readings = function () {
        spinner_utility.show();
        sensor_service.property_sensor_usage(
          $scope.inventory.view_id,
          $scope.organization.id,
          $scope.interval.selected,
          [] // Not excluding any sensors from the query
        ).then(function (usage) {
          // update the base data and reset filters
          property_sensor_usage = usage;

          resetSelections();
          $scope.applyFilters();
          spinner_utility.hide();
        });
      };
      
      $scope.open_data_logger_upload_modal = function () {
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
            datasets: function () {
              return dataset_service.get_datasets().then(function (result) {
                return result.datasets;
              });
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
