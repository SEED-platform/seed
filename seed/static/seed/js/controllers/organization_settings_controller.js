/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.organization_settings', []).controller('organization_settings_controller', [
  '$scope',
  '$uibModal',
  'urls',
  'organization_payload',
  'auth_payload',
  'organization_service',
  'property_column_names',
  'taxlot_column_names',
  'meters_service',
  '$translate',
  function (
    $scope,
    $uibModal,
    urls,
    organization_payload,
    auth_payload,
    organization_service,
    property_column_names,
    taxlot_column_names,
    meters_service,
    $translate
  ) {
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
    $scope.property_column_names = property_column_names;
    $scope.taxlot_column_names = taxlot_column_names;
    $scope.org_static = angular.copy($scope.org);

    $scope.unit_options_eui = [{
      label: $translate.instant('kBtu/sq. ft./year'),
      value: 'kBtu/ft**2/year'
    }, {
      label: $translate.instant('GJ/m²/year'),
      value: 'GJ/m**2/year'
    }, {
      label: $translate.instant('MJ/m²/year'),
      value: 'MJ/m**2/year'
    }, {
      label: $translate.instant('kWh/m²/year'),
      value: 'kWh/m**2/year'
    }, {
      label: $translate.instant('kBtu/m²/year'),
      value: 'kBtu/m**2/year'
    }];

    // Ideally, these units and types for meters should be translatable.
    $scope.chosen_type_unit = {
      type: null,
      unit: null
    };

    // Energy type option executed within this method in order to repeat on organization update
    var get_energy_type_options = function () {
      $scope.energy_type_options = _.map($scope.org.display_meter_units, function (unit, type) {
        return {
          label: type + ' | ' + unit,
          value: type
        };
      });
    };
    get_energy_type_options();

    meters_service.valid_energy_types_units().then(function (results) {
      $scope.energy_unit_options = results;
    });

    $scope.get_valid_units_for_type = function () {
      var options = $scope.energy_unit_options[$scope.chosen_type_unit.type];
      var previous_unit = $scope.org.display_meter_units[$scope.chosen_type_unit.type];
      if (_.includes(options, previous_unit)) {
        $scope.chosen_type_unit.unit = previous_unit;
      } else {
        $scope.chosen_type_unit.unit = null;
      }
    };

    // Called when save_settings is called to update the scoped org before org save request is sent.
    var update_display_unit_for_scoped_org = function () {
      var type = $scope.chosen_type_unit.type;
      var unit = $scope.chosen_type_unit.unit;

      if (type && unit) {
        $scope.org.display_meter_units[type] = unit;
        get_energy_type_options();
      }
    };

    $scope.unit_options_area = [{
      label: $translate.instant('square feet'),
      value: 'ft**2'
    }, {
      label: $translate.instant('square metres'),
      value: 'm**2'
    }];

    $scope.significant_figures_options = [{
      label: '0',
      value: 0
    }, {
      label: '0.1',
      value: 1
    }, {
      label: '0.02',
      value: 2
    }, {
      label: '0.003',
      value: 3
    }, {
      label: '0.0004',
      value: 4
    }];

    $scope.thermal_conversion_countries = [{
      label: 'US',
      value: 1
    }, {
      label: 'Canada',
      value: 2
    }];

    $scope.confirm_delete = function (org) {
      $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/delete_org_modal.html',
        controller: 'delete_org_modal_controller',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          org: org
        }
      });
    };

    $scope.resize_textarea = function () {
      const input = document.getElementById('new-user-email-content');
      input.style.height = '34px';
      input.style.height = input.scrollHeight + 'px';
    };

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
      $scope.settings_updated = false;
      update_display_unit_for_scoped_org();
      organization_service.save_org_settings($scope.org).then(function () {
        $scope.settings_updated = true;
        $scope.org_static = angular.copy($scope.org);
        $scope.$emit('organization_list_updated');
        // $scope.$emit('app_error', data);
      });
    };
  }]);
