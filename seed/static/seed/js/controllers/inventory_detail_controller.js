/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail', [])
  .controller('inventory_detail_controller', [
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
      $scope.organization = user_service.get_organization();

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

      $scope.inventory = {
        view_id: $stateParams.view_id,
        related: $scope.inventory_type === 'properties' ? inventory_payload.taxlots : inventory_payload.properties
      };
      $scope.cycle = inventory_payload.cycle;
      $scope.labels = _.filter(labels_payload, function (label) {
        return !_.isEmpty(label.is_applied);
      });

      /** See service for structure of returned payload */
      $scope.historical_items = inventory_payload.history;
      $scope.item_state = inventory_payload.state;

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

      $scope.gotoMeasureAnchor = function (x) {
        $location.hash('measureAnchor' + x);
        $anchorScroll();
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
       * Compare edits with original
       */
      $scope.diff = function () {
        if (_.isEmpty($scope.item_copy)) return {};
        // $scope.item_state, $scope.item_copy
        var result = {};
        _.forEach($scope.item_state, function (value, key) {
          if (key === 'extra_data') return;
          if (value === $scope.item_copy[key]) return;
          if (_.isNull($scope.item_copy[key]) && _.isString(value) && _.isEmpty(value)) return;
          if (_.isNumber($scope.item_copy[key]) && _.isString(value) && $scope.item_copy[key] === _.toNumber(value)) return;

          _.set(result, key, value);
        });
        _.forEach($scope.item_state.extra_data, function (value, key) {
          if (value === $scope.item_copy.extra_data[key]) return;
          if (_.isNull($scope.item_copy.extra_data[key]) && _.isString(value) && _.isEmpty(value)) return;
          if (_.isNumber($scope.item_copy.extra_data[key]) && _.isString(value) && $scope.item_copy.extra_data[key] === _.toNumber(value)) return;

          _.set(result, 'extra_data.' + key, value);
        });

        return result;
      };

      /**
       * Check if the edits are actually modified
       */
      $scope.modified = function () {
        return !_.isEmpty($scope.diff());
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
        if ($scope.inventory_type === 'properties') {
          inventory_service.update_property($scope.inventory.view_id, $scope.diff())
            .then(function (data) {
              if (_.has(data, 'view_id')) {
                $state.go('inventory_detail', {
                  inventory_type: 'properties',
                  view_id: data.view_id
                });
                var otherMergedRecords = data.match_merged_count - 1;
                Notification.info({
                  message: otherMergedRecords === 1 ? '1 other record was matched and merged.' : otherMergedRecords + ' other records were matched and merged.',
                  delay: 10000
                });
              } else {
                // In the short term, we're just refreshing the page after a save so the table
                // shows new history.
                // TODO: Refactor so that table is dynamically updated with new information
                $state.reload();
              }
            })
            .catch(function (data) {
              $log.error(String(data));
            });
        } else if ($scope.inventory_type === 'taxlots') {
          inventory_service.update_taxlot($scope.inventory.view_id, $scope.diff())
            .then(function (data) {
              if (_.has(data, 'view_id')) {
                $state.go('inventory_detail', {
                  inventory_type: 'taxlots',
                  view_id: data.view_id
                });
                var otherMergedRecords = data.match_merged_count - 1;
                Notification.info({
                  message: otherMergedRecords === 1 ? '1 other record was matched and merged.' : otherMergedRecords + ' other records were matched and merged.',
                  delay: 10000
                });
              } else {
                // In the short term, we're just refreshing the page after a save so the table
                // shows new history.
                // TODO: Refactor so that table is dynamically updated with new information
                $state.reload();
              }
            })
            .catch(function (data) {
              $log.error(String(data));
            });
        }
      };

      /** Open a model to edit labels for the current detail item. */

      $scope.open_update_labels_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/update_item_labels_modal.html',
          controller: 'update_item_labels_modal_controller',
          resolve: {
            inventory_ids: function () {
              return [$scope.inventory.view_id];
            },
            inventory_type: function () {
              return $scope.inventory_type;
            }
          }
        });
        modalInstance.result.then(function () {
          label_service.get_labels($scope.inventory_type, [$scope.inventory.view_id]).then(function (labels) {
            $scope.labels = _.filter(labels, function (label) {
              return !_.isEmpty(label.is_applied);
            });
          });
        }, function () {
          // Do nothing
        });
      };

      $scope.unmerge = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/unmerge_modal.html',
          controller: 'unmerge_modal_controller',
          resolve: {
            inventory_type: function () {
              return $scope.inventory_type;
            }
          }
        });

        return modalInstance.result.then(function () {
          if ($scope.inventory_type === 'properties') {
            return matching_service.unmergeProperties($scope.inventory.view_id);
          } else {
            return matching_service.unmergeTaxlots($scope.inventory.view_id);
          }
        }).then(function (result) {
          $state.go('inventory_detail', {
            inventory_type: $scope.inventory_type,
            view_id: result.view_id
          });
        });
      };

      $scope.export_building_sync = function () {
        var the_url = '/api/v2_1/properties/' + $stateParams.view_id + '/building_sync/';
        $http.get(the_url, {})
          .then(function (response) {
            var blob = new Blob([response.data], {type: 'application/xml;charset=utf-8;'});
            var downloadLink = angular.element('<a></a>');
            var filename = 'buildingsync_property_' + $stateParams.view_id + '.xml';
            downloadLink.attr('href', $window.URL.createObjectURL(blob));
            downloadLink.attr('download', filename);
            downloadLink[0].click();
          });
      };

      $scope.export_building_sync_xlsx = function () {
        var filename = 'buildingsync_property_' + $stateParams.view_id + '.xlsx';
        // var profileId = null;
        // if ($scope.currentProfile) {
        //   profileId = $scope.currentProfile.id;
        // }

        $http.post('/api/v2.1/tax_lot_properties/export/', {
          ids: [$stateParams.view_id],
          filename: filename,
          profile_id: null, // TODO: reconfigure backend to handle detail settings profiles
          export_type: 'xlsx'
        }, {
          params: {
            organization_id: $scope.organization.id,
            cycle_id: $scope.cycle.id,
            inventory_type: $scope.inventory_type
          },
          responseType: 'arraybuffer'
        }).then(function (response) {
          var blob_type = response.headers()['content-type'];

          var blob = new Blob([response.data], {type: blob_type});
          saveAs(blob, filename);
        });
      };

      $scope.unpair_property_from_taxlot = function (property_id) {
        pairing_service.unpair_property_from_taxlot($scope.inventory.view_id, property_id);
        $state.reload();
      };

      $scope.unpair_taxlot_from_property = function (taxlot_id) {
        pairing_service.unpair_taxlot_from_property($scope.inventory.view_id, taxlot_id);
        $state.reload();
      };

      $scope.uploader = {
        invalid_xml_extension_alert: false,
        in_progress: false,
        progress: 0,
        complete: false,
        status_message: ''
      };

      $scope.uploaderfunc = function (event_message, file, progress) {
        switch (event_message) {
          case 'invalid_xml_extension':
            $scope.uploader.invalid_xml_extension_alert = true;
            break;

          case 'upload_submitted':
            $scope.uploader.filename = file.filename;
            $scope.uploader.invalid_xml_extension_alert = false;
            $scope.uploader.in_progress = true;
            $scope.uploader.status_message = 'uploading file';
            break;

          case 'upload_error':
            $scope.uploader.status_message = 'upload failed';
            $scope.uploader.complete = false;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 0;
            alert(file.error);
            break;

          case 'upload_in_progress':
            $scope.uploader.in_progress = true;
            $scope.uploader.progress = 100 * progress.loaded / progress.total;
            break;

          case 'upload_complete':
            $scope.uploader.status_message = 'upload complete';
            $scope.uploader.complete = true;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 100;
            $state.reload();
            break;
        }

        _.defer(function () {
          $scope.$apply();
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

    }]);
