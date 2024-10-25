/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.meter_edit_modal', []).controller('meter_edit_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'inventory_group_service',
  'meter_service',
  'spinner_utility',
  'organization_id',
  'group_id',
  'meter',
  'property_id',
  'system_id',
  'view_id',
  'refresh_meters_and_readings',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    inventory_group_service,
    meter_service,
    spinner_utility,
    organization_id,
    group_id,
    meter,
    property_id,
    system_id,
    view_id,
    refresh_meters_and_readings
  ) {
    $scope.loading = true;
    $scope.meter_type = property_id ? "Property" : "System";
    $scope.config = {}

    inventory_group_service.get_groups_for_inventory("properties", [property_id], include_systems=true).then((groups) => {
      $scope.potentialGroups = groups;
      $scope.group_options = groups;
      $scope.potentialSystems = groups.flatMap((group) => group.systems)
      $scope.system_options = $scope.potentialSystems
    }).then(() => {
      set_config()
    });

    $scope.update_meter = () => {
      if ($scope.meter_type == 'Property') {
        meter_service.update_meter_connection(organization_id, view_id, meter.id, $scope.config).then(() => {
          refresh_meters_and_readings();
          spinner_utility.show();
          $uibModalInstance.dismiss('cancel');
        });
      }
    };
    const set_config = () => {
      // const connection_type = meter.connection_type.toLowerCase()
      const outflow_options = ['To Outside', 'From Patron to Service', 'Total To Patron']
      // const inflow_options = ['From Outside', 'From Service to Patron', 'Total From Patron']
      let direction = 'inflow'
      if (outflow_options.includes(meter.connection_type)) {
        direction = 'outflow'
      }

      const connection = meter.connection_type.includes('Outside') ? 'outside' : 'service'
      const use = meter.property_id ? 'using' : 'offering'
      let system_id
      if (meter.system_id) {
        system = $scope.system_options.find(system => system.id == meter.system_id)
        $scope.service_options = system.services
      }

      if (meter.service_id) {
        const system = $scope.potentialSystems.find(
          (system) => system.services.some((service) => service.id === meter.service_id)
        )
        $scope.service_options = system.services;
        system_id = system.id;
      }

      $scope.config = {
        direction: direction,
        connection: connection,
        use: use,
        group_id: meter.service_group,
        system_id: system_id,
        service_id: meter.service_id,
      }

      $scope.loading = false;
    }

  
    $scope.$watchCollection("config", () => {
      $scope.form_valid = false;
      outside = $scope.config.direction && $scope.config.connection === 'outside'
      all_truthy = Object.values($scope.config).every(value => Boolean(value))
      if (outside || all_truthy) {
        $scope.form_valid = true;
      }
    })

    $scope.direction_options = [
      {display: "Flowing In", value: "inflow"}, 
      {display: "Flowing Out", value: "outflow"}
    ]
    $scope.connection_options = [
      {display: "Connected to Outside", value: "outside"},
      {display: "Connected to a Service", value: "service"} 
    ]
    $scope.use_options = [
      {display: "Using a Service", value: "using"}, 
    ]

    // SELECTION LOGIC
    $scope.connection_selected = () => {
      // if outside, user is done.
      if ($scope.config.connection !== 'outside') {
        // $scope.show_usage = true;
        // if a property meter, show all groups. otherwise system_id will dictate group_id
        if ($scope.meter_type == "Property") {
          $scope.config.use = 'using';
          // $scope.show_groups = true;
          $scope.group_options = $scope.potentialGroups;
        }
      } else {
        // reset values
        keys = ['use', 'group_id', 'system_id', 'service_id']
        keys.forEach(key => $scope.config[key] = null);
      }
    };

    $scope.use_selected = () => {
      console.log('use_selected')
    }

    $scope.group_selected = () => {
      console.log('group_selected')
      $scope.system_options = $scope.potentialGroups.find(group => group.id === $scope.config.group_id).systems
    }

    $scope.system_selected = () => {
      console.log('system_selected')
      $scope.service_options = $scope.system_options.find(system => system.id === $scope.config.system_id).services
    }


    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    const init = () => {
      if (system_id) {
        $scope.use_options.push({ display: "Offering a Service (Total)", value: "offering" })
      }
    }
    init()
  }
]);
