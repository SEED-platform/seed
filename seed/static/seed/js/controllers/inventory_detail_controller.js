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
    'label_helper_service',
    'label_service',
    'inventory_service',
    'inventory_payload',
    'all_columns',
    'default_columns',
    'labels_payload',
    function ($state, $scope, $uibModal, $log, $filter, $stateParams, urls, label_helper_service, label_service,
              inventory_service, inventory_payload, all_columns, default_columns, labels_payload) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        id: $stateParams.inventory_id,
        related: $scope.inventory_type == 'properties' ? inventory_payload.taxlots : inventory_payload.properties
      };
      $scope.cycle = inventory_payload.cycle;
      $scope.fields = all_columns.fields;
      $scope.labels = _.filter(labels_payload, function (label) {
        return !_.isEmpty(label.is_applied);
      });

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
          lbl.label = label_helper_service.lookup_label(lbl.color);
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
       * generate_data_fields: returns a list of objects representing
       * the data fields (fixed column and extra_data) to show for
       * the current item in the detail view (Property or State).
       *
       * This method makes sure keys/fields are not duplicated.
       * Also, it only adds columns that are in the
       * default_columns property (if any exist).
       *
       * @param {Object}  state_obj              A 'state' object (for a Property or TaxLot) of key/value pairs
       * @param {Array}   default_columns      An array of key names for columns selected by user for display
       * @param {Array}   extra_data_keys      An array of key names for all extra_data fields
       *                                        (in current state or past states)
       *
       * @returns {Array} data_fields: A list of data_field objects
       *
       */
      $scope.generate_data_fields = function (state_obj, default_columns, extra_data_keys) {

        var data_fields = [];
        var key_list = [];
        var check_defaults = (default_columns && default_columns.length > 0);
        if (!extra_data_keys) {
          extra_data_keys = [];
        }

        // add Property fixed_column properties to data_fields
        angular.forEach(state_obj, function (val, key) {
          // Duplicate check and check if default_columns is used and if field in columns
          if (!_.isUndefined(val) && $scope.is_valid_data_column_key(key) && !_.includes(key_list, key) &&
            (!check_defaults || (check_defaults && _.includes(default_columns, key)))) {
            key_list.push(key);
            data_fields.push({
              key: key,
              type: 'fixed_column'
            });
          }
        });

        // add Property extra_data from all states to data_fields
        angular.forEach(extra_data_keys, function (key) {
          // Duplicate check and check if default_columns is used and if field in columns
          if ($scope.is_valid_data_column_key(key) && !_.includes(key_list, key) &&
            (!check_defaults || (check_defaults && _.includes(default_columns, key)))) {
            key_list.push(key);
            data_fields.push({
              key: key,
              type: 'extra_data'
            });
          }
        });

        if (check_defaults) {
          // Sort by user defined order.
          data_fields.sort(function (a, b) {
            if (default_columns.indexOf(a.key) < default_columns.indexOf(b.key)) {
              return -1;
            } else {
              return 1;
            }
          });
        } else {
          // Sort alphabetically.
          data_fields.sort(function (a, b) {
            if (a.key.toLowerCase() < b.key.toLowerCase()) {
              return -1;
            } else {
              return 1;
            }
          });
        }

        return data_fields;
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


        $scope.data_fields = $scope.generate_data_fields($scope.item_state, $scope.default_columns, $scope.all_extra_data_keys);
      };

      // fired on controller loaded
      init();

    }]);
