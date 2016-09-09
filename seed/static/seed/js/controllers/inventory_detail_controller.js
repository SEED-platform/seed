/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail', [])
  .controller('inventory_detail_controller', [
    '$controller',
    '$state',
    '$scope',
    '$uibModal',
    '$log',
    '$filter',
    '$stateParams',
    'urls',
    'label_helper_service',
    'inventory_service',
    'inventory_payload',
    'all_columns',
    'default_columns',
    function ($controller, $state, $scope, $uibModal, $log, $filter, $stateParams, urls, label_helper_service,
              inventory_service, inventory_payload, all_columns, default_columns) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        id: $stateParams.inventory_id,
        related: $scope.inventory_type == 'properties' ? inventory_payload.taxlots : inventory_payload.properties
      };
      $scope.cycle = inventory_payload.cycle;
      $scope.fields = all_columns.fields;

      /** See service for structure of returned payload */
      $scope.historical_items = inventory_payload.history;

      $scope.item_state = inventory_payload.state;
      $scope.changed_fields = inventory_payload.changed_fields;

      // The server provides of *all* extra_data keys (across current state and all historical state)
      // Let's remember this.
      $scope.all_extra_data_keys = inventory_payload.extra_data_keys;

      $scope.item_title = 'Property : ' + ($scope.item_state.address_line_1 ? $scope.item_state.address_line_1 : '(no address 1)');
      $scope.user = {};
      $scope.user_role = inventory_payload.user_role;


      /** Instantiate 'parent' controller class,
       *  where the more generic methods for editing a detail item are located.
       *  (Methods in this child class are more specific to a 'Property' detail item.) */
      $controller('base_detail_controller', {
        $scope: $scope, $uibModal: $uibModal,
        $log: $log, inventory_service: inventory_service,
        all_columns: all_columns, urls: urls, $filter: $filter,
        label_helper_service: label_helper_service,
        default_columns: default_columns
      });


      /**
       * User clicked 'save' button
       */
      $scope.on_save = function () {
        $scope.save_item();
      };

      /**
       * save_item: saves the user's changes to the Property/TaxLot State object.
       */
      $scope.save_item = function () {
        $scope.$emit('show_saving');
        if ($scope.inventory_type == 'properties') {
          inventory_service.update_property($scope.inventory.id, $scope.cycle.id, $scope.item_state)
            .then(function (data) {
                // In the short term, we're just refreshing the page after a save so the table
                // shows new history.
                // TODO: Refactor so that table is dynamically updated with new information
                $scope.$emit('finished_saving');
                $state.reload();
              }, function (data, status) {
                // reject promise
                $scope.$emit('finished_saving');
              }
            )
            .catch(function (data) {
              $log.error(String(data));
            });
        } else if ($scope.inventory_type == 'taxlots') {
          inventory_service.update_taxlot($scope.taxlot.id, $scope.cycle.id, $scope.item_state)
            .then(function (data) {
              // In the short term, we're just refreshing the page after a save so the table
              // shows new history.
              // TODO: Refactor so that table is dynamically updated with new information
              $scope.$emit('finished_saving');
              $state.reload();
            }, function (data, status) {
              // reject promise
              $scope.$emit('finished_saving');
            })
            .catch(function (data) {
              $log.error(String(data));
            });
        }
      };

      /**
       *   init: sets default state of inventory detail page,
       *   sets the field arrays for each section, performs
       *   some date string manipulation for better display rendering,
       *   and gets all the extra_data fields
       *
       */
      var init = function () {

        if ($scope.inventory_type == 'properties') {
          $scope.format_date_values($scope.item_state, inventory_service.property_state_date_columns);
        } else if ($scope.inventory_type == 'taxlots') {
          $scope.format_date_values($scope.item_state, inventory_service.taxlot_state_date_columns);
        }


        $scope.data_fields = $scope.generate_data_fields($scope.item_state, $scope.default_columns, $scope.all_extra_data_keys);

        $scope.labels = $scope.init_labels($scope.inventory);
      };

      // fired on controller loaded
      init();

    }]);
