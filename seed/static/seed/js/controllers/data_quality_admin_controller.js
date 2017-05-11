/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_quality_admin', [])
.controller('data_quality_admin_controller', [
  '$scope',
  '$q',
  '$stateParams',
  'all_columns',
  'organization_payload',
  'data_quality_rules_payload',
  'auth_payload',
  'labels_payload',
  'data_quality_service',
  'organization_service',
  'label_service',
  function (
    $scope,
    $q,
    $stateParams,
    all_columns,
    organization_payload,
    data_quality_rules_payload,
    auth_payload,
    labels_payload,
    data_quality_service,
    organization_service,
    label_service
  ) {
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.field_types = [{
      id: null,
      label: ''
    }, {
      id: 'number',
      label: 'Number'
    }, {
      id: 'string',
      label: 'Text'
    }, {
      id: 'date',
      label: 'Date'
    }, {
      id: 'year',
      label: 'Year'
    }];
    $scope.units = ['', 'square feet', 'kBtu/sq. ft./year'];

    $scope.all_columns = all_columns;
    $scope.all_labels = labels_payload;

    var loadRules = function (rules) {
      $scope.ruleGroups = {
        properties: {},
        taxlots: {}
      };
      _.forEach(data_quality_rules_payload.rules, function (type, index) {
        _.forEach(type, function (rule) {
          if (!_.has($scope.ruleGroups[index], rule.field)) $scope.ruleGroups[index][rule.field] = [];
          var row = rule;
          if (row.type === 'date') {
            if (row.min) row.min = moment(row.min, 'YYYYMMDD').toDate();
            if (row.max) row.max = moment(row.max, 'YYYYMMDD').toDate();
          }
          if (rule.label) {
            var match = _.find(labels_payload, function (label) {
              return label.id === rule.label;
            });
            if (match) {
              row.label = match.name;
            }
          }
          $scope.ruleGroups[index][rule.field].push(row);
        });
      });
    };
    loadRules(data_quality_rules_payload);

    // Restores the default rules
    $scope.restore_defaults = function () {
      $scope.defaults_restored = false;
      data_quality_service.reset_default_data_quality_rules($scope.org.org_id).then(function (rules) {
        loadRules(rules);
        $scope.defaults_restored = true;
      }, function (data, status) {
        $scope.$emit('app_error', data);
      });
    };

    // Reset all rules
    $scope.reset_all_rules = function () {
      $scope.rules_reset = false;
      data_quality_service.reset_all_data_quality_rules($scope.org.org_id).then(function (rules) {
        loadRules(rules);
        $scope.rules_reset = true;
      }, function (data, status) {
        $scope.$emit('app_error', data);
      });
    };

    // Saves the configured rules
    $scope.save_settings = function () {
      $scope.rules_updated = false;
      var rules = {
        properties: [],
        taxlots: []
      };
      var promises = [];
      _.forEach($scope.ruleGroups, function (rules_types, rule_type) {
        _.forEach(rules_types, function (field_rules, field) {
          _.forEach(field_rules, function (row) {
            var d = $q.defer();
            promises.push(d.promise);
            var r = {
              field: row.field,
              type: row.type,
              required: row.required,
              not_null: row.not_null,
              enabled: row.enabled,
              min: row.min || null,
              max: row.max || null,
              severity: row.severity,
              units: row.units,
              label: row.label,
              'delete': row.delete
            };
            if (row.type === 'date') {
              if (row.min) r.min = Number(moment(row.min).format('YYYYMMDD'));
              if (row.max) r.max = Number(moment(row.max).format('YYYYMMDD'));
            }
            if (row.new) {
              var match = _.find(labels_payload, function (label) {
                return label.name === row.label;
              });
              if (!match) {
                var newLabel = {
                  name: row.label,
                  color: 'gray',
                  label: 'default'
                };
                label_service.create_label_for_org($scope.org.id, newLabel).then(angular.bind(this, function (result) {
                    r.label = result.id;
                    rules[rule_type].push(r);
                    d.resolve();
                  }, rule_type),
                  function (message) {
                    $log.error('Error creating new label.', message);
                    d.reject();
                  }).then(function () {
                    label_service.get_labels_for_org($scope.org.id).then(function (labels) {
                      $scope.all_labels = labels;  
                    });
                  });
              }
              else {
                r.label = match.id;
                rules[rule_type].push(r);
                d.resolve();
              }
              row.new = null;
            }
            else {
              rules[rule_type].push(r);
              d.resolve();
            }
          });
        });
      });
      $q.all(promises)
        .then(function () {
          organization_service.save_data_quality_rules($scope.org.org_id, rules).then(function (data) {
            $scope.rules_updated = true;
          }, function (data, status) {
            $scope.$emit('app_error', data);
          });
        })
        .catch(function () {
        });
    };

    // capture rule field dropdown change.
    $scope.change_field = function (rule, oldField, index) {
      var original = rule.type;
      var newType = _.find(all_columns.fields, {name: rule.field}).type;

      // clear columns that are type specific.
      if (newType !== original) {
        rule.min = null;
        rule.max = null;
        rule.units = '';
      }

      rule.type = newType;

      // modify the custom label if the rule is recently added.
      if (rule.new) {
        rule.label = 'Invalid ' + _.find(all_columns.fields, {name: rule.field}).displayName;
      }

      // move rule to appropriate spot in ruleGroups.
      if (!_.has($scope.ruleGroups[$scope.inventory_type], rule.field)) $scope.ruleGroups[$scope.inventory_type][rule.field] = [];
      $scope.ruleGroups[$scope.inventory_type][rule.field].push(rule);
      // remove old rule.
      if ($scope.ruleGroups[$scope.inventory_type][oldField].length === 1) delete $scope.ruleGroups[$scope.inventory_type][oldField];
      else $scope.ruleGroups[$scope.inventory_type][oldField].splice(index, 1);
      rule.autofocus = true;
    };

    // Keep field types consistent for identical fields
    $scope.change_type = function (rule) {
      var type = rule.type;
      _.forEach($scope.ruleGroups[$scope.inventory_type][rule.field], function (currentRule) {
        currentRule.min = null;
        currentRule.max = null;
        currentRule.type = type;
      });
    };

    // Keep "required field" consistent for identical fields
    $scope.change_required = function (rule) {
      var required = !rule.required;
      _.forEach($scope.ruleGroups[$scope.inventory_type][rule.field], function (currentRule) {
        currentRule.required = required;
      });
    };

    // Keep "not null" consistent for identical fields
    $scope.change_not_null = function (rule) {
      var not_null = !rule.not_null;
      _.forEach($scope.ruleGroups[$scope.inventory_type][rule.field], function (currentRule) {
        currentRule.not_null = not_null;
      });
    };

    // create a new rule.
    $scope.create_new_rule = function () {
      var field = all_columns.fields[0].name || null;
      var label = all_columns.fields[0].displayName || '';
      var type = all_columns.fields[0].type || null;

      if (field) {
        if (!_.has($scope.ruleGroups[$scope.inventory_type], field)) $scope.ruleGroups[$scope.inventory_type][field] = [];

        $scope.ruleGroups[$scope.inventory_type][field].push({
          enabled: true,
          field: field,
          displayName: label,
          type: type,
          required: false,
          not_null: false,
          max: null,
          min: null,
          severity: 'error',
          units: '',
          label: 'Invalid ' + label,
          'new': true,
          autofocus: true
        });
      }
    };

    // set rule as deleted.
    $scope.delete_rule = function (rule, index) {
      rule.delete = true;
      if (rule.new) {
        if ($scope.ruleGroups[$scope.inventory_type][rule.field].length === 1) delete $scope.ruleGroups[$scope.inventory_type][rule.field];
        else $scope.ruleGroups[$scope.inventory_type][rule.field].splice(index, 1);
      }
    };
  }]);
