/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail', [])
  .controller('inventory_detail_controller', [
    '$state',
    '$scope',
    '$uibModal',
    '$log',
    '$filter',
    '$stateParams',
    'urls',
    'label_service',
    'inventory_service',
    'inventory_payload',
    'columns',
    'labels_payload',
    function ($state, $scope, $uibModal, $log, $filter, $stateParams, urls, label_service,
              inventory_service, inventory_payload, columns, labels_payload) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        id: $stateParams.inventory_id,
        related: $scope.inventory_type == 'properties' ? inventory_payload.taxlots : inventory_payload.properties
      };
      $scope.cycle = inventory_payload.cycle;
      $scope.labels = _.filter(labels_payload, function (label) {
        return !_.isEmpty(label.is_applied);
      });

      var localStorageKey = 'grid.' + $scope.inventory_type + '.detail';

      $scope.columns = inventory_service.loadSettings(localStorageKey, angular.copy(columns));

      /** See service for structure of returned payload */
      $scope.historical_items = inventory_payload.history;

      $scope.item_state = inventory_payload.state;
      $scope.changed_fields = inventory_payload.changed_fields;

      // The server provides of *all* extra_data keys (across current state and all historical state)
      // Let's remember this.
      $scope.all_extra_data_keys = inventory_payload.extra_data_keys;

      $scope.user = {};
      $scope.user_role = inventory_payload.user_role;


      $scope.edit_form_showing = false;

      /** Holds a copy of original state of item_state.
       *  Used when 'Cancel' is selected and item should be
       *  returned to original state. */
      $scope.item_copy = {};

      /** An array of fields to show to user,
       *  populated according to settings.*/
      $scope.data_fields = [];


      $scope.status = {
        isopen: false
      };

      $scope.init_labels = function (item) {
        return _.map(item.labels, function (lbl) {
          lbl.label = label_service.lookup_label(lbl.color);
          return lbl;
        });
      };

      /* User clicked 'cancel' button */
      $scope.on_cancel = function () {
        $scope.restore_copy();
        $scope.edit_form_showing = false;
      };

      /* User clicked 'edit' link */
      $scope.on_edit = function () {
        $scope.make_copy_before_edit();
        $scope.edit_form_showing = true;
      };

      /**
       * save_property_state: saves the property state in case cancel gets clicked
       */
      $scope.make_copy_before_edit = function () {
        $scope.item_copy = angular.copy($scope.item_state);
      };

      /**
       * restore_property: restores the property state from its copy
       */
      $scope.restore_copy = function () {
        $scope.item_state = $scope.item_copy;
      };

      /**
       * is_valid_key: checks to see if the key or attribute should be excluded
       *   from being copied from parent to master building
       *
       *    TODO Update these for v2...I've removed keys that were obviously old (e.g. canonical)
       */
      $scope.is_valid_data_column_key = function (key) {
        var known_invalid_keys = [
          'children',
          'confidence',
          'created',
          'extra_data',
          'extra_data_sources',
          'id',
          'is_master',
          'import_file',
          'import_file_name',
          'last_modified_by',
          'match_type',
          'modified',
          'model',
          'parents',
          'pk',
          'super_organization',
          'source_type',
          'duplicate'
        ];
        var no_invalid_key = !_.includes(known_invalid_keys, key);

        return (!_.includes(key, '_source') && !_.includes(key, 'extra_data') && !_.includes(key, '$$') && no_invalid_key);
      };

      /**
       * returns a number
       */
      $scope.get_number = function (num) {
        if (!angular.isNumber(num) && !_.isNil(num)) {
          return +num.replace(/,/g, '');
        }
        return num;
      };


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
          inventory_service.update_taxlot($scope.inventory.id, $scope.cycle.id, $scope.item_state)
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

      /** Open a model to edit labels for the current detail item.
       *
       * @param inventory_id  A Property or TaxLot ID
       * @param inventory_type  "properties" or "taxlots"
       */

      $scope.open_update_labels_modal = function (inventory_id, inventory_type) {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/update_item_labels_modal.html',
          controller: 'update_item_labels_modal_controller',
          resolve: {
            inventory_ids: function () {
              return [inventory_id];
            },
            inventory_type: function () {
              return inventory_type;
            }
          }
        });
        modalInstance.result.then(function () {
            label_service.get_labels([inventory_id], {
              inventory_type: $stateParams.inventory_type
            }).then(function (labels) {
              $scope.labels = _.filter(labels, function (label) {
                return !_.isEmpty(label.is_applied);
              });
            });
          }, function (message) {
            //dialog was 'dismissed,' which means it was cancelled...so nothing to do.
          }
        );
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
      };

      init();

    }]);
