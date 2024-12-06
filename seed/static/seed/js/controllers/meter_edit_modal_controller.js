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
    $scope.property_id = property_id;

    const group_fn = property_id ?
      inventory_group_service.get_groups_for_inventory.bind(null, 'properties', [property_id]) :
      inventory_group_service.get_groups.bind(null, 'properties');

    group_fn().then((groups) => {
      $scope.potentialGroups = groups;
      $scope.group_options = property_id ? groups : groups.filter((g) => $scope.group_id === g.id);
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
      $scope.config = { ...meter.config };
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
      { display: 'Imported', value: 'imported' },
      { display: 'Exported', value: 'exported' }
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
      // reset downstream values
      const keys = ['use', 'group_id', 'system_id', 'service_id'];
      keys.forEach((key) => { $scope.config[key] = null; });

      // if outside, form is complete.
      if ($scope.config.connection === 'outside') return;

      // if a property meter, show all groups. otherwise system_id will dictate group_id
      if (property_id) {
        $scope.config.use = 'using';
        $scope.group_options = $scope.potentialGroups;
      }
    };

    $scope.use_selected = () => {
      // reset downstream values
      const keys = ['group_id', 'system_id', 'service_id'];
      keys.forEach((key) => { $scope.config[key] = null; });
      $scope.service_options = [];
      const group = $scope.potentialGroups.find((g) => g.id === $scope.group_id);

      // if this is a *system* meter, we know the group already.
      if (system_id) {
        $scope.group_options = [group];
        $scope.config.group_id = $scope.group_id;
        $scope.group_selected();
      }

      // if this meter is *offering*, we already know the group and system
      if ($scope.config.use === 'offering') {
        const system = group.systems.find((s) => s.id === system_id);
        $scope.system_options = [system];
        $scope.config.system_id = system.id;
        $scope.system_selected();
      }
    };

    $scope.group_selected = () => {
      $scope.system_options = $scope.potentialGroups.find((group) => group.id === $scope.config.group_id).systems;
      $scope.service_options = [];
    };

    $scope.system_selected = () => {
      if ($scope.system_options.length) {
        $scope.service_options = $scope.system_options.find((system) => system.id === $scope.config.system_id).services;
      }
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
