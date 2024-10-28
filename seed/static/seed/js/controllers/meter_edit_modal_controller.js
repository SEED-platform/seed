/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.meter_edit_modal', []).controller('meter_edit_modal_controller', [
  '$scope',
  '$stateParams',
  '$uibModalInstance',
  'inventory_group_service',
  'inventory_service',
  'meter_service',
  'spinner_utility',
  'organization_id',
  'meter',
  'property_id',
  'system_id',
  'view_id',
  'refresh_meters_and_readings',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $stateParams,
    $uibModalInstance,
    inventory_group_service,
    inventory_service,
    meter_service,
    spinner_utility,
    organization_id,
    meter,
    property_id,
    system_id,
    view_id,
    refresh_meters_and_readings
  ) {
    $scope.loading = true;
    $scope.meter_parent = property_id ? `Property ${property_id}` : meter.system_name;
    $scope.config = {};
    $scope.group_id = $stateParams.group_id;

    const group_fn = property_id ?
      inventory_group_service.get_groups_for_inventory.bind(null, 'properties', [property_id]) :
      inventory_group_service.get_groups.bind(null, 'properties');

    group_fn().then((groups) => {
      $scope.potentialGroups = groups;
      $scope.group_options = groups;
      $scope.potentialSystems = groups.flatMap((group) => group.systems);
      $scope.system_options = $scope.potentialSystems;
    }).then(() => {
      set_config();
    });

    if (property_id && !view_id) {
      // if no view_id, get first.
      inventory_service.get_property_views(organization_id, meter.property_id).then((response) => {
        view_id = response.property_views[0].id;
      });
    }

    $scope.update_meter = () => {
      meter_service.update_meter_connection(organization_id, meter.id, $scope.config, view_id, $scope.group_id).then((response) => {
        if (response.status === 200) {
          refresh_meters_and_readings();
          spinner_utility.show();
          $uibModalInstance.dismiss('cancel');
        } else {
          $scope.error = response.data.message;
        }
      });
    };

    const set_config = () => {
      $scope.config = meter.config;
      if ($scope.potentialGroups.length && meter.config.system_id) {
        const system = $scope.system_options.find((system) => system.id === meter.config.system_id);
        $scope.service_options = system.services;
      }
      $scope.loading = false;
    };

    $scope.$watchCollection('config', () => {
      $scope.form_valid = false;
      const outside = $scope.config.direction && $scope.config.connection === 'outside';
      const all_truthy = Object.values($scope.config).every((value) => Boolean(value));
      if (outside || all_truthy) {
        $scope.form_valid = true;
      }
    });

    $scope.direction_options = [
      { display: 'Flowing In', value: 'inflow' },
      { display: 'Flowing Out', value: 'outflow' }
    ];
    $scope.connection_options = [
      { display: 'Connected to Outside', value: 'outside' },
      { display: 'Connected to a Service', value: 'service' }
    ];
    $scope.use_options = [
      { display: 'Using a Service', value: 'using' }
    ];

    // SELECTION LOGIC
    $scope.connection_selected = () => {
      // if outside, form is complete.
      if ($scope.config.connection !== 'outside') {
        // if a property meter, show all groups. otherwise system_id will dictate group_id
        if (property_id) {
          $scope.config.use = 'using';
          $scope.group_options = $scope.potentialGroups;
        }
      } else {
        // reset downstream values
        const keys = ['use', 'group_id', 'system_id', 'service_id'];
        keys.forEach((key) => { $scope.config[key] = null; });
      }
    };

    $scope.group_selected = () => {
      $scope.system_options = $scope.potentialGroups.find((group) => group.id === $scope.config.group_id).systems;
    };

    $scope.system_selected = () => {
      $scope.service_options = $scope.system_options.find((system) => system.id === $scope.config.system_id).services;
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss('cancel');
    };

    const init = () => {
      if (system_id) {
        $scope.use_options.push({ display: 'Offering a Service (Total)', value: 'offering' });
      }
    };
    init();
  }
]);
