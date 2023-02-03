/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.organization_settings', []).controller('organization_settings_controller', [
  '$scope',
  '$uibModal',
  'urls',
  'organization_payload',
  'auth_payload',
  'organization_service',
  'salesforce_mapping_service',
  'salesforce_config_service',
  'property_column_names',
  'taxlot_column_names',
  'labels_payload',
  'salesforce_mappings_payload',
  'salesforce_configs_payload',
  'meters_service',
  'Notification',
  '$translate',
  function (
    $scope,
    $uibModal,
    urls,
    organization_payload,
    auth_payload,
    organization_service,
    salesforce_mapping_service,
    salesforce_config_service,
    property_column_names,
    taxlot_column_names,
    labels_payload,
    salesforce_mappings_payload,
    salesforce_configs_payload,
    meters_service,
    Notification,
    $translate
  ) {
    $scope.org = organization_payload.organization;

    $scope.conf = {};
    if (salesforce_configs_payload.length > 0) {
      $scope.conf = salesforce_configs_payload[0];
    }

    $scope.auth = auth_payload.auth;
    $scope.property_column_names = property_column_names;
    $scope.taxlot_column_names = taxlot_column_names;
    $scope.salesforce_mappings = salesforce_mappings_payload;
    $scope.org_static = angular.copy($scope.org);
    $scope.labels = labels_payload;
    $scope.test_sf = false;
    $scope.test_sf_msg = null;
    $scope.sync_sf = false;
    $scope.sync_sf_msg = null;
    $scope.form_errors = null;
    $scope.table_errors = null;
    $scope.config_errors = null;
    $scope.changes_possible = false;
    $scope.secrets = {pwd: 'password', token: 'password'}

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

    $scope.decimal_places_options = [{
      label: '0 (e.g., 0)',
      value: 0
    }, {
      label: '1 (e.g., 0.1)',
      value: 1
    }, {
      label: '2 (e.g., 0.12)',
      value: 2
    }, {
      label: '3 (e.g., 0.123)',
      value: 3
    }, {
      label: '4 (e.g., 0.1234)',
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
      $scope.form_errors = null;
      update_display_unit_for_scoped_org();
      organization_service.save_org_settings($scope.org).then(function () {

        $scope.settings_updated = true;
        $scope.org_static = angular.copy($scope.org);
        $scope.$emit('organization_list_updated');

      })
      .catch(function (response) {
        if (response.data && response.data.status == 'error'){
          $scope.form_errors = response.data.message;
        } else {
          $scope.form_errors = 'An unknown error has occurred';
        }

      });

      // also save salesforce configs
      if ($scope.org.salesforce_enabled) {
        if ($scope.conf.id){
          // update
          salesforce_config_service.update_salesforce_config($scope.conf.id, $scope.conf)
          .then(function (response) {
            if (response.status == 'error'){
              $scope.config_errors = response.errors;
            } else {
              salesforce_config_service.get_salesforce_configs($scope.org.id)
              .then( function (data) {
                $scope.conf = (data.length > 0) ? data[0] : {}
              })
            }
          })
          .catch(function (response) {
            if (response.data && response.data.status == 'error') {
              $scope.config_errors = response.data.message;
            } else {
              $scope.config_errors = 'An unknown error has occurred';
            }
            console.log("config ERRORS: ", $scope.config_errors);
          });
        } else {
          // create
          salesforce_config_service.new_salesforce_config($scope.conf)
          .then(function () {
            salesforce_config_service.get_salesforce_configs($scope.org.id)
            .then( function (data) {
              $scope.conf = (data.length > 0) ? data[0] : {}
            })
          })
          .catch(function (response) {
            if (response.data && response.data.status == 'error'){
              $scope.config_errors = response.data.message;
            } else {
              $scope.config_errors = 'An unknown error has occurred';
            }
            console.log("CONFIG ERRORS: ", $scope.config_errors);
          });
        }
      }

      // also save NEW/UPDATED salesforce mappings if any
      let promises = [];
      if ($scope.changes_possible) {
        _.forEach($scope.salesforce_mappings, function (mapping) {
          let promise = null;
          if (mapping.id) {
            // has ID, update call
            promise = salesforce_mapping_service.update_salesforce_mapping(mapping.id, mapping)
            .catch(function (response) {
              if (response.data && response.data.status == 'error') {
                $scope.table_errors = response.data.message;
              } else {
                $scope.table_errors = 'An unknown error has occurred';
              }
              console.log("TABLE ERRORS: ", $scope.table_errors);
            });
          } else {
            // no ID, save new
            promise = salesforce_mapping_service.new_salesforce_mapping(mapping)
            .catch(function (response) {
              if (response.data && response.data.status == 'error'){
                $scope.table_errors = response.data.message;
              } else {
                $scope.table_errors = 'An unknown error has occurred';
              }
              console.log("TABLE ERRORS: ", $scope.table_errors);
            });
          }
          promises.push(promise);
        });
        return Promise.all(promises)
        .then(function(results) {
            return results.join();
            $scope.changes_possible = false;

            // retrieve mappings again
            salesforce_mapping_service.get_salesforce_mappings()
            .then(function (response) {
              $scope.salesforce_mappings = response;
            });
        });


      }
    };

    // flag unsaved changes in mappings table
    $scope.flag_change = function () {
      $scope.changes_possible = true;
    };

    // Add and remove column methods
    $scope.add_new_column = function () {
      var empty_row = {id: null, salesforce_fieldname: '', column: null, organization: $scope.org.id};

      if ($scope.salesforce_mappings[0]) {
        $scope.salesforce_mappings.push(empty_row);
      } else {
        $scope.salesforce_mappings = [empty_row];
      }
      $scope.flag_change();
    };

    // TODO: add a 'are you sure?' modal before deletion
    $scope.remove_column = function (index) {
      if ($scope.salesforce_mappings[index].id) {
        // remove from db
        salesforce_mapping_service.delete_salesforce_mapping($scope.salesforce_mappings[index].id)
        .then(function () {
          $scope.salesforce_mappings.splice(index, 1);
        })
        .catch(function (response) {
          if (response.data && response.data.status == 'error'){
            $scope.table_errors = response.data.message;
          } else {
            $scope.table_errors = 'An unknown error has occurred';
          }
          console.log("TABLE ERRORS: ", $scope.table_errors);
        });
      }
      else {
        // not saved to db yet, just remove from table
        $scope.salesforce_mappings.splice(index, 1);
      }

    };

    /**
     * toggle secret fields
    */
    $scope.toggle_secret = function(field) {
      $scope.secrets[field] = ($scope.secrets[field] == 'password') ? 'text' : 'password';
    }

    /**
     * run the sync salesforce process
    */
    $scope.sync_salesforce = function () {
      $scope.sync_sf = null;
      $scope.sync_sf_msg = null;
      salesforce_config_service.sync_salesforce().then(function (response) {
        $scope.sync_sf = 'success';
        // reload configs to grab new update date
        salesforce_config_service.get_salesforce_configs($scope.org.id)
        .then( function (data) {
          $scope.conf = (data.length > 0) ? data[0] : {}
        })
        // show notification
        Notification.success({
          message: ("Salesforce Sync Successful!"),
          delay: 4000
        });
      })
      .catch(function (response) {
        $scope.sync_sf = 'error';
        if (response.data && response.data.message){
          $scope.sync_sf_msg = response.data.message;
        } else {
          $scope.sync_sf_msg = 'Unknown Error'
        }
      });
    }

    /**
     * reset the last update date (to null)
    */
    $scope.reset_date = function () {

      $scope.conf.last_update_date = null;
      $scope.save_settings();
      Notification.success({
        message: ("Reset successful!"),
        delay: 4000
      });
    }

    /**
     * tests the salesforce connection
    */
    $scope.test_connection = function () {
      $scope.test_sf = null;
      $scope.test_sf_msg = null;

      // test connection: if works, set to success, if fails set to error.
      salesforce_config_service.salesforce_connection($scope.conf).then(function (response) {
        $scope.test_sf = 'success';
      })
      .catch(function (response) {
        $scope.test_sf = 'error';
        if (response.data && response.data.message){
          $scope.test_sf_msg = response.data.message;
        } else {
          $scope.test_sf_msg = 'Unknown Error'
        }
      });

    };
  }]);
