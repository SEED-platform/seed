/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_cycles', [])
  .controller('inventory_detail_cycles_controller', [
    '$http',
    '$state',
    '$scope',
    '$uibModal',
    '$log',
    '$filter',
    '$stateParams',
    '$anchorScroll',
    '$location',
    '$window',
    'Notification',
    'urls',
    'spinner_utility',
    'label_service',
    'inventory_service',
    'matching_service',
    'pairing_service',
    'user_service',
    'inventory_payload',
    'columns',
    'profiles',
    'current_profile',
    'labels_payload',
    function (
      $http,
      $state,
      $scope,
      $uibModal,
      $log,
      $filter,
      $stateParams,
      $anchorScroll,
      $location,
      $window,
      Notification,
      urls,
      spinner_utility,
      label_service,
      inventory_service,
      matching_service,
      pairing_service,
      user_service,
      inventory_payload,
      columns,
      profiles,
      current_profile,
      labels_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;

      // Detail Settings Profile
      $scope.profiles = profiles;
      $scope.currentProfile = current_profile;

      if ($scope.currentProfile) {
        $scope.columns = [];
        _.forEach($scope.currentProfile.columns, function (col) {
          var foundCol = _.find(columns, {id: col.id});
          if (foundCol) $scope.columns.push(foundCol);
        });
      } else {
        // No profiles exist
        $scope.columns = _.reject(columns, 'is_extra_data');
      }

      $scope.isDisabledField = function (name) {
        return _.includes([
          'analysis_end_time',
          'analysis_start_time',
          'analysis_state',
          'analysis_state_message',
          'geocoding_confidence',
          'campus',
          'created',
          'updated'
        ], name);
      };

      // $scope.inventory = {
      //   view_id: $stateParams.view_id,
      //   related: $scope.inventory_type === 'properties' ? inventory_payload.taxlots : inventory_payload.properties
      // };

      /** See service for structure of returned payload */
      $scope.historical_items = inventory_payload.history;
      // $scope.item_state = inventory_payload.state;

      // item_parent is the property or the tax lot instead of the PropertyState / TaxLotState
      if ($scope.inventory_type === 'properties') {
        $scope.item_parent = inventory_payload.property;
      } else {
        $scope.item_parent = inventory_payload.taxlot;
      }

      $scope.changed_fields = inventory_payload.changed_fields;

      // The server provides of *all* extra_data keys (across current state and all historical state)
      // Let's remember this.
      $scope.all_extra_data_keys = inventory_payload.extra_data_keys;

      $scope.user = {};
      $scope.user_role = inventory_payload.user_role;

      /** An array of fields to show to user,
       *  populated according to settings.*/
      $scope.data_fields = [];

      var ignoreNextChange = true;
      $scope.$watch('currentProfile', function (newProfile) {
        if (ignoreNextChange) {
          ignoreNextChange = false;
          return;
        }

        inventory_service.save_last_detail_profile(newProfile.id, $scope.inventory_type);
        spinner_utility.show();
        $window.location.reload();
      });

      /**
       * Iterate through all object values and format
       * those we recognize as a 'date' value
       */
      $scope.format_date_values = function (state_obj, date_columns) {
        if (!state_obj || !state_obj.length) return;
        if (!date_columns || !date_columns.length) return;

        // Look for each 'date' type value in all Property State values
        // and update format accordingly.
        _.forEach(date_columns, function (key) {
          if (state_obj[key]) {
            state_obj[key] = $filter('date')(state_obj[key], 'MM/dd/yyyy');
          }
        });
      };

      /**
       *   init: sets default state of inventory detail page,
       *   sets the field arrays for each section, performs
       *   some date string manipulation for better display rendering,
       *   and gets all the extra_data fields
       *
       */
      var init = function () {
        if ($scope.inventory_type === 'properties') {
          $scope.format_date_values($scope.item_state, inventory_service.property_state_date_columns);
        } else if ($scope.inventory_type === 'taxlots') {
          $scope.format_date_values($scope.item_state, inventory_service.taxlot_state_date_columns);
        }
      };

      init();
      console.log("$scope.historical_items", $scope.historical_items);
      console.log("$scope.columns", $scope.columns);
    }]);
