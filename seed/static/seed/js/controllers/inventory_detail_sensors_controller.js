angular.module('BE.seed.controller.inventory_detail_sensors', [])
  .controller('inventory_detail_sensors_controller', [
    '$scope',
    '$stateParams',
    'inventory_payload',
    'sensors',
    'property_sensor_usage',
    'spinner_utility',
    'organization_payload',
    function (
      $scope,
      $stateParams,
      inventory_payload,
      sensors,
      property_sensor_usage,
      spinner_utility,
      organization_payload,
    ) {
      spinner_utility.show();
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.organization = organization_payload.organization;
      $scope.property_sensor_usage = property_sensor_usage;

      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      var getSensorLabel = function (sensor) {
        return sensor.display_name + " - " + sensor.units;
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

      $scope.data = property_sensor_usage.readings.map(reading => {
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

      var sorted_sensors = _.sortBy(sensors, ['id']);
      resetSelections();

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
