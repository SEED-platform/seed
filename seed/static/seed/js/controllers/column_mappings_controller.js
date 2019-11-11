/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.column_mappings', [])
  .controller('column_mappings_controller', [
    '$scope',
    '$q',
    '$state',
    '$stateParams',
    '$uibModal',
    'Notification',
    'column_mappings_service',
    'spinner_utility',
    'column_mappings',
    'inventory_service',
    'organization_payload',
    'auth_payload',
    function (
      $scope,
      $q,
      $state,
      $stateParams,
      $uibModal,
      Notification,
      column_mappings_service,
      spinner_utility,
      column_mappings,
      inventory_service,
      organization_payload,
      auth_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;

      $scope.state = $state.current;

      $scope.filter_params = {};

      $scope.property_count = column_mappings.property_count;
      $scope.taxlot_count = column_mappings.taxlot_count;
      $scope.column_mappings = column_mappings.column_mappings;

      $scope.mappable_property_columns = inventory_service.get_property_columns().then(function (result) {

      });
      $scope.mappable_taxlot_columns = inventory_service.get_taxlot_columns().then(function (result) {

      });
      // console.log($scope.mappable_property_columns);
      // console.log($scope.mappable_taxlot_columns);

      $scope.delete_mapping = function (id) {
        column_mappings_service.delete_column_mapping_for_org($scope.org.id, id).then(function () {
          _.remove($scope.column_mappings,
            {id: id});
          if ($scope.inventory_type === 'properties') {
            --$scope.property_count;
          } else {
            --$scope.taxlot_count;
          }
        });
      };

      $scope.delete_all_mappings = function () {
        $scope.mappings_deleted = false;

        var promises = [];
        _.forEach($scope.column_mappings, function (mapping) {
          promises.push($scope.delete_mapping(mapping.id));
        });

        spinner_utility.show();
        $q.all(promises).then(function (results) {
          $scope.mappings_deleted = true;
          var totalChanged = results.length;
          Notification.success('Successfully deleted ' + totalChanged + ' column mapping' + (totalChanged === 1 ? '' : 's'));
        }, function (data) {
          $scope.$emit('app_error', data);
        }).finally(function () {
          spinner_utility.hide();
        });
      };

      $scope.mock_mappings = {
        "PM Imports as of 20191104": [
          {"from_field": "Property Id", "from_units": null, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
          {"from_field": "Property Name", "from_units": null, "to_field": "Property Name", "to_table_name": "PropertyState"},
          {"from_field": "Parent Property Id", "from_units": null, "to_field": "PM Parent Property ID", "to_table_name": "PropertyState"},
          {"from_field": "Parent Property Name", "from_units": null, "to_field": "Some Parent Property Name", "to_table_name": "PropertyState"},
          {"from_field": "Year Ending", "from_units": null, "to_field": "Year Ending Test", "to_table_name": "PropertyState"},
          {"from_field": "Electricity Use - Grid Purchase (kWh)", "from_units": null, "to_field": "Electricity Use - Grid Purchase (kWh)", "to_table_name": "PropertyState"},
          {"from_field": "Natural Gas Use (therms)", "from_units": null, "to_field": "Natural Gas Use (therms)", "to_table_name": "PropertyState"},
          {"from_field": "ENERGY STAR Score", "from_units": null, "to_field": "Energy Score", "to_table_name": "PropertyState"},
          {"from_field": "Site Energy Use (kBtu)", "from_units": "GJ/m**2/year", "to_field": "Site", "to_table_name": "PropertyState"},
          {"from_field": "Source Energy Use (kBtu)", "from_units": "kBtu/m**2/year", "to_field": "Source EUI Modeled", "to_table_name": "PropertyState"},
          {"from_field": "Site EUI (kBtu/ft2)", "from_units": "kWh/m**2/year", "to_field": "Site EUI", "to_table_name": "PropertyState"},
          {"from_field": "Source EUI (kBtu/ft2)", "from_units": "MJ/m**2/year", "to_field": "Source EUI", "to_table_name": "PropertyState"},
          {"from_field": "Total GHG Emissions (Metric Tons CO2e)", "from_units": null, "to_field": "Total GHG Emissions (Metric Tons CO2e)", "to_table_name": "PropertyState"},
          {"from_field": "Total GHG Emissions Intensity (kgCO2e/ft2)", "from_units": null, "to_field": "Total GHG Emissions Intensity (kgCO2e/ft2)", "to_table_name": "PropertyState"},
          {"from_field": "On Behalf Of", "from_units": null, "to_field": "On Behalf Of", "to_table_name": "PropertyState"},
          {"from_field": "Organization", "from_units": null, "to_field": "Some Organization Test Change", "to_table_name": "PropertyState"},
          {"from_field": "Phone", "from_units": null, "to_field": "Owner", "to_table_name": "PropertyState"},
          {"from_field": "Email", "from_units": null, "to_field": "Owner Email", "to_table_name": "PropertyState"},
          {"from_field": "Generation Date", "from_units": null, "to_field": "Generation Date", "to_table_name": "PropertyState"},
          {"from_field": "Release Date", "from_units": null, "to_field": "Release Date", "to_table_name": "PropertyState"}
        ],
        "PM Imports with missing email as of 20191104": [
          {"from_field": "Property Id", "from_units": null, "to_field": "PM Property ID", "to_table_name": "PropertyState"},
          {"from_field": "Property Name", "from_units": null, "to_field": "Property Name", "to_table_name": "PropertyState"},
          {"from_field": "Parent Property Id", "from_units": null, "to_field": "PM Parent Property ID", "to_table_name": "PropertyState"},
          {"from_field": "Parent Property Name", "from_units": null, "to_field": "Some Parent Property Name", "to_table_name": "PropertyState"},
          {"from_field": "Year Ending", "from_units": null, "to_field": "Year Ending Test", "to_table_name": "PropertyState"},
          {"from_field": "Electricity Use - Grid Purchase (kWh)", "from_units": null, "to_field": "Electricity Use - Grid Purchase (kWh)", "to_table_name": "PropertyState"},
          {"from_field": "Natural Gas Use (therms)", "from_units": null, "to_field": "Natural Gas Use (therms)", "to_table_name": "PropertyState"},
          {"from_field": "ENERGY STAR Score", "from_units": null, "to_field": "Energy Score", "to_table_name": "PropertyState"},
          {"from_field": "Site Energy Use (kBtu)", "from_units": "GJ/m**2/year", "to_field": "Site", "to_table_name": "PropertyState"},
          {"from_field": "Source Energy Use (kBtu)", "from_units": "kBtu/m**2/year", "to_field": "Source EUI Modeled", "to_table_name": "PropertyState"},
          {"from_field": "Site EUI (kBtu/ft2)", "from_units": "kWh/m**2/year", "to_field": "Site EUI", "to_table_name": "PropertyState"},
          {"from_field": "Source EUI (kBtu/ft2)", "from_units": "MJ/m**2/year", "to_field": "Source EUI", "to_table_name": "PropertyState"},
          {"from_field": "Total GHG Emissions (Metric Tons CO2e)", "from_units": null, "to_field": "Total GHG Emissions (Metric Tons CO2e)", "to_table_name": "PropertyState"},
          {"from_field": "Total GHG Emissions Intensity (kgCO2e/ft2)", "from_units": null, "to_field": "Total GHG Emissions Intensity (kgCO2e/ft2)", "to_table_name": "PropertyState"},
          {"from_field": "On Behalf Of", "from_units": null, "to_field": "On Behalf Of", "to_table_name": "PropertyState"},
          {"from_field": "Organization", "from_units": null, "to_field": "Some Organization Test Change", "to_table_name": "PropertyState"},
          {"from_field": "Phone", "from_units": null, "to_field": "Owner", "to_table_name": "PropertyState"},
          {"from_field": "Generation Date", "from_units": null, "to_field": "Generation Date", "to_table_name": "PropertyState"},
          {"from_field": "Release Date", "from_units": null, "to_field": "Release Date", "to_table_name": "PropertyState"}
        ],
      };

      $scope.mock_presets = Object.keys($scope.mock_mappings);
      $scope.dropdown_selected_preset = $scope.current_preset = $scope.mock_presets[0];

      $scope.changes_possible = false;

      $scope.toggle_change_flag = function () {
        $scope.changes_possible = true;
      }

      $scope.check_for_changes = function () {
        if ($scope.changes_possible) {
          $uibModal.open({
            template: '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch profiles without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch Presets</button></div>'
          }).result.then(function () {
            $scope.changes_possible = true;
          }).catch(function () {
            $scope.dropdown_selected_preset = $scope.current_preset
          });
        }

        // if changes were made to currently applied preset, open modal to confirm action
          // if confirmed, initialize_mappings and change applied_preset to dropdown_selected_preset
          // if cancelled, do nothing
      };

      $scope.add_new_column = function () {
        $scope.mock_mappings[$scope.dropdown_selected_preset].push(
          {"from_field": "", "from_units": null, "to_field": "", "to_table_name": ""}
        );
      };

      $scope.remove_column = function (index) {
        $scope.mock_mappings[$scope.dropdown_selected_preset].splice(index, 1);
      };
    }]);
