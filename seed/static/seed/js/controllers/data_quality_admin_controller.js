/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_quality_admin', [])
.controller('data_quality_admin_controller', [
  '$scope',
  '$q',
  'all_columns',
  'organization_payload',
  'data_quality_rules_payload',
  'auth_payload',
  'labels_payload',
  'organization_service',
  'label_service',
  'urls',
  function (
    $scope,
    $q,
    all_columns,
    organization_payload,
    data_quality_rules_payload,
    auth_payload,
    labels_payload,
    organization_service,
    label_service,
    urls
  ) {
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.units = ['', 'square feet', 'kBtu/sq. ft./year'];

    $scope.all_columns = all_columns;
    $scope.all_labels  = labels_payload;
    $scope.rules_type  = 'properties';

    /* TEMP - split data into assumed structure for properties and taxlots.  TODO - remove once structure is in place.
    var len = data_quality_rules_payload.in_range_checking.length;
    var results = {
      properties: data_quality_rules_payload.in_range_checking.slice(0, len/2),
      taxlots:    data_quality_rules_payload.in_range_checking.slice(len/2)
    }
    data_quality_rules_payload.in_range_checking = results;
    */

    var loadRules = function (rules) {
      $scope.rows = {
        properties: {},
        taxlots:    {}
      };
      _.forEach(rules.in_range_checking, function (type, index) {
        _.forEach(type, function (rule) {
          if (!$scope.rows[index].hasOwnProperty(rule.field)) $scope.rows[index][rule.field] = [];
          var row         = _.pick(rule, ['enabled', 'type', 'min', 'max', 'severity', 'units', 'label']);
          row.field       = _.find(all_columns.fields, {name: rule.field}).name;
          row.displayName = _.find(all_columns.fields, {name: rule.field}).displayName;
          if (row.type === 'date') {
            if (row.min) row.min = moment(row.min, 'YYYYMMDD').toDate();
            if (row.max) row.max = moment(row.max, 'YYYYMMDD').toDate();
          }
          $scope.rows[index][rule.field].push(row);
        });
      });
    };
    loadRules(data_quality_rules_payload);

    // Restores the default rules
    $scope.restore_defaults = function () {
      $scope.defaults_restored = false;
      organization_service.reset_data_quality_rules($scope.org.org_id).then(function (rules) {
        loadRules(rules);
        $scope.defaults_restored = true;
      }, function (data, status) {
        $scope.$emit('app_error', data);
      });
    };

    // Saves the configured rules
    $scope.save_settings = function () {
      $scope.rules_updated = false;
      var rules = {
        missing_matching_field: data_quality_rules_payload.missing_matching_field,
        missing_values: data_quality_rules_payload.missing_values,
        in_range_checking: {
          properties: [],
          taxlots:    []
        }
      };
      var promises = [];
      _.forEach($scope.rows, function (rules_types, rule_type) {
        _.forEach(rules_types, function (field_rules, field) {
          _.forEach(field_rules, function (row) {
            var d = $q.defer();
            promises.push(d.promise);
            var r = {
              field:    row.field,
              type:     row.type,
              required: row.required,
              null:     row.null,
              enabled:  row.enabled,
              type:     row.type,
              min:      row.min || null,
              max:      row.max || null,
              severity: row.severity,
              units:    row.units,
              label:    row.label,
              delete:   row.delete
            };
            if (row.type === 'date') {
              if (row.min) r.min = Number(moment(row.min).format('YYYYMMDD'));
              if (row.max) r.max = Number(moment(row.max).format('YYYYMMDD'));
            }
            if (row.new) {
              var match = _.find(labels_payload, function(label) {
                return label.name === row.label;
              });
              if(!match) {
                var newLabel = {
                  name:  row.label,
                  color: 'gray',
                  label: 'default'
                };
                label_service.create_label_for_org($scope.org.id, newLabel).then(angular.bind(this, function(result) {
                  r.label = result.id;
                  rules.in_range_checking[rule_type].push(r);
                  d.resolve();
                }, rule_type),
                function(message) {
                  $log.error('Error creating new label.', message);
                  d.reject();
                });
              }
              else {
                r.label = match.id;
                rules.in_range_checking[rule_type].push(r);
                d.resolve();
              }
              row.new = null;
            }
            else {
              rules.in_range_checking[rule_type].push(r);
              d.resolve();
            }
          });
        });
      });
      $q.all(promises)
      .then(function() {
      	organization_service.save_data_quality_rules($scope.org.org_id, rules).then(function (data) {
          $scope.rules_updated = true;
        }, function (data, status) {
          $scope.$emit('app_error', data);
        });
      })
      .catch(function() {
      });
    };

    // capture rule field dropdown change.
    $scope.change_field = function(rule, oldField, index) {
      var original = rule.type;
      var newType  = _.find(all_columns.fields, { name: rule.field }).type;

      // clear columns that are type specific.
      if(newType !== original) {
        rule.min   = null;
        rule.max   = null;
        rule.units = '';
      }

      rule.type = newType;

      // modify the custom label if the rule is recently added.
      if(rule.new) {
        rule.label = 'Invalid ' + _.find(all_columns.fields, { name: rule.field }).displayName;
      }

      // move rule to appropriate spot in array.
      if (!$scope.rows[$scope.rules_type].hasOwnProperty(rule.field)) $scope.rows[$scope.rules_type][rule.field] = [];
      $scope.rows[$scope.rules_type][rule.field].push(rule);
      // remove old rule.
      $scope.rows[$scope.rules_type][oldField].splice(index, 1);
    };

    // create a new rule.
    $scope.create_new_rule = function() {
      var field = all_columns.fields[0].name || null;
      var label = all_columns.fields[0].displayName || '';
      var type  = all_columns.fields[0].type || null;

      if(field) {
        if (!$scope.rows[$scope.rules_type].hasOwnProperty(field)) $scope.rows[$scope.rules_type][field] = [];

        $scope.rows[$scope.rules_type][field].push({
          enabled:     true,
          field:       field,
          displayName: label,
          type:        type,
          required:    null,
          null:        null,
          max:         null,
          min:         null,
          severity:    'error',
          units:       '',
          label:       'Invalid ' + label,
          new:         true
        });
      }
    };

    // set rule as deleted.
    $scope.delete_rule = function(rule, index) {
      rule.delete = true;
      if(rule.new) {
        $scope.rows[$scope.rules_type][rule.field].splice(index, 1);
      }
    };

    // change list view.
    $scope.view = function(type) {
      $scope.rules_type = type;
    };
  }]);
