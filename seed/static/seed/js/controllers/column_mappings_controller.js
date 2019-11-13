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
    'column_mapping_presets',
    'spinner_utility',
    'column_mappings',
    'inventory_service',
    'organization_payload',
    'auth_payload',
    'urls',
    function (
      $scope,
      $q,
      $state,
      $stateParams,
      $uibModal,
      Notification,
      column_mappings_service,
      column_mapping_presets,
      spinner_utility,
      column_mappings,
      inventory_service,
      organization_payload,
      auth_payload,
      urls,
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

      $scope.presets = column_mapping_presets;

      $scope.dropdown_selected_preset = $scope.current_preset = $scope.presets[0];

      $scope.new_preset = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/column_mapping_preset_modal.html',
          controller: 'column_mapping_preset_modal_controller',
          resolve: {
            action: _.constant('new'),
            data: _.constant($scope.dropdown_selected_preset),
            org_id: _.constant($scope.org.id),
          }
        });

        modalInstance.result.then(function (new_preset) {
          $scope.presets.push(new_preset);
          $scope.dropdown_selected_preset = $scope.current_preset = _.last($scope.presets);
          $scope.changes_possible = false;
        });
      };

      $scope.changes_possible = false;

      $scope.flag_change = function () {
        $scope.changes_possible = true;
      }

      $scope.check_for_changes = function () {
        if ($scope.changes_possible) {
          $uibModal.open({
            template: '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch profiles without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch Presets</button></div>'
          }).result.then(function () {
            $scope.changes_possible = false;
          }).catch(function () {
            $scope.dropdown_selected_preset = $scope.current_preset;
          });
        }
      };

      $scope.add_new_column = function () {
        $scope.dropdown_selected_preset.mappings.push(
          {"from_field": "", "from_units": null, "to_field": "", "to_table_name": ""}
        );
        $scope.flag_change();
      };

      $scope.remove_column = function (index) {
        $scope.dropdown_selected_preset.mappings.splice(index, 1);
        $scope.flag_change();
      };
    }]);
