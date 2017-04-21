/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.cleansing_admin', [])
.controller('cleansing_admin_controller', [
  '$scope',
  '$q',
  'all_columns',
  'organization_payload',
  'cleansing_rules_payload',
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
    cleansing_rules_payload,
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

    var loadRules = function (rules) {
      $scope.rows = {};
      _.forEach(rules.in_range_checking, function (rule) {
        if (!$scope.rows.hasOwnProperty(rule.field)) $scope.rows[rule.field] = [];
        var row = _.pick(rule, ['enabled', 'type', 'min', 'max', 'severity', 'units', 'label']);
        row.title = _.find(all_columns.fields, {sort_column: rule.field}).sort_column;
        if (row.type === 'date') {
          if (row.min) row.min = moment(row.min, 'YYYYMMDD').toDate();
          if (row.max) row.max = moment(row.max, 'YYYYMMDD').toDate();
        }
        $scope.rows[rule.field].push(row);
      });
    };
    loadRules(cleansing_rules_payload);

    // Restores the default rules
    $scope.restore_defaults = function () {
      $scope.defaults_restored = false;
      organization_service.reset_cleansing_rules($scope.org.org_id).then(function (rules) {
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
        missing_matching_field: cleansing_rules_payload.missing_matching_field,
        missing_values: cleansing_rules_payload.missing_values,
        in_range_checking: []
      };
      var promises = [];
      _.forEach($scope.rows, function (field_rules, field) {
        _.forEach(field_rules, function (row) {
          var d = $q.defer();
          promises.push(d.promise);
          var r = {
            field: field,
            type: row.type,
            required: row.required,
            null: row.null,
            enabled: row.enabled,
            type: row.type,
            min: row.min || null,
            max: row.max || null,
            severity: row.severity,
            units: row.units,
            label: row.label,
            delete: row.delete
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
              label_service.create_label_for_org($scope.org.id, newLabel).then(function(result) {
                r.label = result.id;
                rules.in_range_checking.push(r);
                d.resolve();
              },
              function(message) {
                $log.error('Error creating new label.', message);
                d.reject();
              });
            }
            else {
              r.label = match.id;
              rules.in_range_checking.push(r);
              d.resolve();
            }
          }
          else {
            rules.in_range_checking.push(r);
            d.resolve();            
          }
        });
      });
      $q.all(promises)
      .then(function() {
        console.log('rules', rules);
        organization_service.save_cleansing_rules($scope.org.org_id, rules).then(function (data) {
          $scope.rules_updated = true;
        }, function (data, status) {
          $scope.$emit('app_error', data);
        });
      })
      .catch(function() {
      });
    };

    // capture rule field dropdown change.
    $scope.change_field = function(rule) {
      var original = rule.type;
      var newType  = _.find(all_columns.fields, { sort_column: rule.title }).type;

      // clear columns that are type specific.
      if(newType !== original) {
        rule.min   = null;
        rule.max   = null;
        rule.units = '';
      }

      rule.type = newType;

      // modify the custom label if the rule is recently added.
      if(rule.new) {
        rule.label = 'Invalid ' + _.find(all_columns.fields, { sort_column: rule.title }).title;
      }
    };

    // create a new rule.
    $scope.create_new_rule = function() {
      var field = all_columns.fields[0].sort_column || null;
      var label = all_columns.fields[0].title || '';
      var type  = all_columns.fields[0].type || null;

      if(field) {
        if (!$scope.rows.hasOwnProperty(field)) $scope.rows[field] = [];

        $scope.rows[field].push({
          enabled:  false,
          title:    field,
          type:     type,
          required: null,
          null:     null,
          max:      null,
          min:      null,
          severity: 'error',
          units:    '',
          label:    'Invalid ' + label,
          new:      true
        });
      }
    };

    // set rule as deleted.
    $scope.delete_rule = function(rule, index) {
      rule.delete = true;
      if(rule.new) {
        $scope.rows[rule.title].splice(index, 1);
      }
    };
  }]);
