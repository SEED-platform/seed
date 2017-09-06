/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_quality_admin', [])
.controller('data_quality_admin_controller', [
  '$scope',
  '$q',
  '$state',
  '$stateParams',
  'columns',
  'organization_payload',
  'data_quality_rules_payload',
  'auth_payload',
  'labels_payload',
  'data_quality_service',
  'organization_service',
  'label_service',
  'spinner_utility',
  '$uibModal',
  'urls',
  'naturalSort',
  'flippers',
  function ($scope,
            $q,
            $state,
            $stateParams,
            columns,
            organization_payload,
            data_quality_rules_payload,
            auth_payload,
            labels_payload,
            data_quality_service,
            organization_service,
            label_service,
            spinner_utility,
            $uibModal,
            urls,
            naturalSort,
            flippers) {
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
    $scope.ruleGroups = {};

    $scope.state = $state.current;

    $scope.data_types = [
      {id: null, label: ''},
      {id: 'number', label: 'Number'},
      {id: 'string', label: 'Text'},
      {id: 'date', label: 'Date'},
      {id: 'year', label: 'Year'}
    ];

    if (flippers.is_active('release:use_pint')) {

      $scope.data_types = [
        {id: null, label: ''},
        {id: 'number', label: 'Number'},
        {id: 'string', label: 'Text'},
        {id: 'date', label: 'Date'},
        {id: 'year', label: 'Year'},
        {id: 'area', label: 'Area'},
        {id: 'eui', label: 'EUI'}
      ];

    }

    $scope.units = [
      {id: null, label: ''},
      {id: 'square feet', label: 'square feet'},
      {id: 'kBtu/sq. ft./year', label: 'kBtu/sq. ft./year'}
    ];

    if (flippers.is_active('release:use_pint')) {

      $scope.units = [
        {id: null, label: ''},
        {id: 'ft**2', label: 'square feet'},
        {id: 'm**2', label: 'square metres'},
        {id: 'kBtu/ft**2/year', label: 'kBtu/sq. ft./year'},
        {id: 'GJ/m**2/year', label: 'GJ/m²/year'},
        {id: 'MJ/m**2/year', label: 'MJ/m²/year'},
        {id: 'kWh/m**2/year', label: 'kWh/m²/year'}
      ];

    }

    $scope.columns = columns;
    $scope.all_labels = labels_payload;
    // console.log(labels_payload)

    var loadRules = function (rules_payload) {
      var ruleGroups = {
        properties: {},
        taxlots: {}
      };
      _.forEach(rules_payload.rules, function (inventory_type, index) {
        _.forEach(inventory_type, function (rule) {
          if (!_.has(ruleGroups[index], rule.field)) ruleGroups[index][rule.field] = [];
          var row = rule;
          if (row.data_type === 'date') {
            if (row.min) row.min = moment(row.min, 'YYYYMMDD').toDate();
            if (row.max) row.max = moment(row.max, 'YYYYMMDD').toDate();
          }
          if (rule.label) {
            // console.log('load: ', rule.label)
            var match = _.find(labels_payload, function (label) {
              // console.log('found: ', label)
              return label.id === rule.label;
            });
            if (match) {
              // console.log('row label: ', match);
              row.label = match;
            }
          }
          ruleGroups[index][rule.field].push(row);
        });
      });

      $scope.ruleGroups = ruleGroups;
    };
    loadRules(data_quality_rules_payload);

    // Restores the default rules
    $scope.restore_defaults = function () {
      spinner_utility.show();
      $scope.defaults_restored = false;
      data_quality_service.reset_default_data_quality_rules($scope.org.org_id).then(function (rules) {
        loadRules(rules);
        $scope.defaults_restored = true;
      }, function (data) {
        $scope.$emit('app_error', data);
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    // Reset all rules
    $scope.reset_all_rules = function () {
      spinner_utility.show();
      $scope.rules_reset = false;
      data_quality_service.reset_all_data_quality_rules($scope.org.org_id).then(function (rules) {
        loadRules(rules);
        $scope.rules_reset = true;
      }, function (data) {
        $scope.$emit('app_error', data);
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    // Saves the configured rules
    $scope.save_settings = function () {
      $scope.rules_updated = false;
      var rules = {
        properties: [],
        taxlots: []
      };
      _.forEach($scope.ruleGroups, function (ruleGroups, inventory_type) {
        _.forEach(ruleGroups, function (ruleGroup) {
          _.forEach(ruleGroup, function (rule) {
            // Skip rules that haven't been assigned to a field yet
            if (rule.field === null) return;

            var r = {
              enabled: rule.enabled,
              field: rule.field,
              data_type: rule.data_type,
              rule_type: rule.rule_type,
              required: rule.required,
              not_null: rule.not_null,
              min: rule.min || null,
              max: rule.max || null,
              text_match: rule.text_match,
              severity: rule.severity,
              units: rule.units,
              label: null
            };
            if (rule.data_type === 'date') {
              if (rule.min) r.min = Number(moment(rule.min).format('YYYYMMDD'));
              if (rule.max) r.max = Number(moment(rule.max).format('YYYYMMDD'));
            }
            if (rule.label) {
              // console.log('la: ', rule.label)
              r.label = rule.label.id;
            }
            if (rule.new) {
              rule.new = null;
              var match = _.find(labels_payload, function (label) {
                return label.name === rule.label;
              });

              if (match) {
                r.label = match.id;
              }
            }
            rules[inventory_type].push(r);
          });
        });
      });

      spinner_utility.show();
      data_quality_service.save_data_quality_rules($scope.org.org_id, rules).then(function (rules) {
        loadRules(rules);
        $scope.rules_updated = true;
      }, function (data) {
        $scope.$emit('app_error', data);
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    // capture rule field dropdown change.
    $scope.change_field = function (rule, oldField, index) {
      if (oldField === '') oldField = null;
      var original = rule.data_type;
      var newDataType = _.find(columns, {name: rule.field}).data_type;

      if (newDataType == undefined) newDataType = null;

      // clear columns that are type specific.
      if (newDataType !== original) {
        rule.text_match = null;
        rule.units = '';

        if (!_.includes([null, 'number'], original) || !_.includes([null, 'number'], newDataType)) {
          // Reset min/max if the data type is something other than null <-> number
          rule.min = null;
          rule.max = null;
        }
      }

      rule.data_type = newDataType;

      // move rule to appropriate spot in ruleGroups.
      if (!_.has($scope.ruleGroups[$scope.inventory_type], rule.field)) $scope.ruleGroups[$scope.inventory_type][rule.field] = [];
      else {
        // Rules already exist for the new field name, so match the data_type, required, and not_null columns
        var existingRule = _.first($scope.ruleGroups[$scope.inventory_type][rule.field]);
        rule.data_type = existingRule.data_type;
        rule.required = existingRule.required;
        rule.not_null = existingRule.not_null;
      }
      $scope.ruleGroups[$scope.inventory_type][rule.field].push(rule);
      // remove old rule.
      if ($scope.ruleGroups[$scope.inventory_type][oldField].length === 1) delete $scope.ruleGroups[$scope.inventory_type][oldField];
      else $scope.ruleGroups[$scope.inventory_type][oldField].splice(index, 1);
      rule.autofocus = true;
    };

    // Keep field types consistent for identical fields
    $scope.change_data_type = function (rule, oldValue) {
      var data_type = rule.data_type;
      _.forEach($scope.ruleGroups[$scope.inventory_type][rule.field], function (currentRule) {
        currentRule.text_match = null;

        if (!_.includes(['', 'number'], oldValue) || !_.includes([null, 'number'], data_type)) {
          // Reset min/max if the data type is something other than null <-> number
          currentRule.min = null;
          currentRule.max = null;
        }
        currentRule.data_type = data_type;
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

    $scope.removeLabelFromRule = function (rule) {
      rule.label = null;
    };

    // create a new rule.
    $scope.create_new_rule = function () {
      var field = null;
      if (!_.has($scope.ruleGroups[$scope.inventory_type], field)) {
        $scope.ruleGroups[$scope.inventory_type][field] = [];
      }

      $scope.ruleGroups[$scope.inventory_type][field].push({
        enabled: true,
        field: field,
        displayName: field,
        data_type: 'number',
        rule_type: 1,
        required: false,
        not_null: false,
        max: null,
        min: null,
        text_match: null,
        severity: 'error',
        units: '',
        // label: 'Invalid ' + label,
        label: null,
        'new': true,
        autofocus: true
      });
    };

    // create label and assign to that rule
    $scope.create_label = function (rule) {
      var modalInstance = $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/data_quality_labels_modal.html',
        controller: 'data_quality_labels_modal_controller',
        resolve: {
          org_id: function () {
            return $scope.org.org_id;
          }
        }
      });
      modalInstance.result.then(function (returnedLabels) {
        rule.label = returnedLabels;

        //code for multiple labels
        // label_service.get_labels().then(function (allLabels) {
        //   console.log('all: ', allLabels)
        //   rule.label = _.filter(allLabels, function (label) {
        //     // console.log(label.id + ' and ' + returnedLabels)
        //     return _.includes(returnedLabels, label.id);
        //   });
        // });

      }, function () {
        // Do nothing
      });
    };

    // set rule as deleted.
    $scope.delete_rule = function (rule, index) {
      if ($scope.ruleGroups[$scope.inventory_type][rule.field].length === 1) delete $scope.ruleGroups[$scope.inventory_type][rule.field];
      else $scope.ruleGroups[$scope.inventory_type][rule.field].splice(index, 1);
    };

    var displayNames = {};
    _.forEach($scope.columns, function (column) {
      displayNames[column.name] = column.displayName;
    });

    $scope.sortedRuleGroups = function () {
      var sortedKeys = _.keys($scope.ruleGroups[$scope.inventory_type]).sort(function (a, b) {
        return naturalSort(displayNames[a], displayNames[b]);
      });
      var nullKey = _.remove(sortedKeys, function (key) {
        return key === 'null';
      });

      // Put created unassigned rows first
      return nullKey.concat(sortedKeys);
    };

    $scope.selectAll = function () {
      var allEnabled = $scope.allEnabled();
      _.forEach($scope.ruleGroups[$scope.inventory_type], function (ruleGroup) {
        _.forEach(ruleGroup, function (rule) {
          rule.enabled = !allEnabled;
        });
      });
    };

    $scope.allEnabled = function () {
      var total = 0;
      var enabled = _.reduce($scope.ruleGroups[$scope.inventory_type], function (result, ruleGroup) {
        total += ruleGroup.length;
        return result + _.filter(ruleGroup, 'enabled').length;
      }, 0);
      return total === enabled;
    };

  }]);
