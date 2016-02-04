/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_cleansing', [])
  .controller('data_cleansing_controller', ['$scope', 'all_columns', 'organization_payload', 'auth_payload', 'organization_service', 'urls', function ($scope, all_columns, organization_payload, auth_payload, organization_service, urls) {
    $scope.fields = all_columns.fields;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    var dateRegexp = /[\d]{2}\/[\d]{2}\/[\d]{4}/;
    $scope.isDate = function(rule) {
      return (rule.min instanceof Date) || (rule.max instanceof Date);
    };

    var rows = {
      year_built: [{
        min: 1700,
        max: 2019,
        severity: 'error',
        units: null
      }],
      year_ending: [{
        min: '01/01/1889',
        max: '12/31/2020',
        severity: 'error',
        units: null
      }],
      conditioned_floor_area: [{
        min: 0,
        max: 7000000,
        severity: 'error',
        units: 'square feet'
      }, {
        min: 100,
        max: null,
        severity: 'warning',
        units: 'square feet'
      }],
      energy_score: [{
        min: 0,
        max: 100,
        severity: 'error',
        units: null
      }, {
        min: 10,
        max: null,
        severity: 'warning',
        units: null
      }],
      generation_date: [{
        min: '01/01/1889',
        max: '12/31/2020',
        severity: 'error',
        units: null
      }],
      gross_floor_area: [{
        min: 100,
        max: 7000000,
        severity: 'error',
        units: 'square feet'
      }],
      occupied_floor_area: [{
        min: 100,
        max: 7000000,
        severity: 'error',
        units: 'square feet'
      }],
      recent_sale_date: [{
        min: '01/01/1889',
        max: '12/31/2020',
        severity: 'error',
        units: null
      }],
      release_date: [{
        min: '01/01/1889',
        max: '12/31/2020',
        severity: 'error',
        units: null
      }],
      site_eui: [{
        min: 0,
        max: 1000,
        severity: 'error',
        units: 'kBtu/sq. ft./year'
      }, {
        min: 10,
        max: null,
        severity: 'warning',
        units: 'kBtu/sq. ft./year'
      }],
      site_eui_weather_normalized: [{
        min: 0,
        max: 1000,
        severity: 'error',
        units: 'kBtu/sq. ft./year'
      }],
      source_eui: [{
        min: 0,
        max: 1000,
        severity: 'error',
        units: 'kBtu/sq. ft./year'
      }, {
        min: 10,
        max: null,
        severity: 'warning',
        units: 'kBtu/sq. ft./year'
      }],
      source_eui_weather_normalized: [{
        min: 10,
        max: 1000,
        severity: 'error',
        units: 'kBtu/sq. ft./year'
      }]
    };

    _.each(_.keys(rows), function(field) {
      var title = _.find($scope.fields, {sort_column: field}).title;
      _.each(rows[field], function(row) {
        row.title = title;
        row.checked = true;
        if (dateRegexp.test(row.min)) row.min = moment(row.min, 'MM/DD/YYYY').toDate();
        if (dateRegexp.test(row.max)) row.max = moment(row.max, 'MM/DD/YYYY').toDate();
      });
    });
    $scope.rows = rows;

    // Restores the default rules
    $scope.restore_defaults = function () {
    };

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
    };

  }]);
