/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.cleansing_admin', [])
.controller('cleansing_admin_controller', [
  '$scope',
  'all_columns',
  'organization_payload',
  'cleansing_rules_payload',
  'auth_payload',
  'organization_service',
  function (
    $scope,
    all_columns,
    organization_payload,
    cleansing_rules_payload,
    auth_payload,
    organization_service
  ) {
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.units = ['', 'square feet', 'kBtu/sq. ft./year'];

    var loadRules = function (rules) {
      $scope.rows = {};
      _.forEach(rules.in_range_checking, function (rule) {
        if (!$scope.rows.hasOwnProperty(rule.field)) $scope.rows[rule.field] = [];
        var row = _.pick(rule, ['enabled', 'type', 'min', 'max', 'severity', 'units']);
        row.title = _.find(all_columns.fields, {sort_column: rule.field}).title;
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
      _.forEach($scope.rows, function (field_rules, field) {
        _.forEach(field_rules, function (row) {
          var r = {
            field: field,
            enabled: row.enabled,
            type: row.type,
            min: row.min || null,
            max: row.max || null,
            severity: row.severity,
            units: row.units
          };
          if (row.type === 'date') {
            if (row.min) r.min = Number(moment(row.min).format('YYYYMMDD'));
            if (row.max) r.max = Number(moment(row.max).format('YYYYMMDD'));
          }
          rules.in_range_checking.push(r);
        });
      });
      organization_service.save_cleansing_rules($scope.org.org_id, rules).then(function (data) {
        $scope.rules_updated = true;
      }, function (data, status) {
        $scope.$emit('app_error', data);
      });
    };

  }]);
