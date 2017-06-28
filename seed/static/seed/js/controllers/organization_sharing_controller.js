/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.organization_sharing', []).controller('organization_sharing_controller', [
  '$scope',
  'all_columns',
  'organization_payload',
  'query_threshold_payload',
  'shared_fields_payload',
  'auth_payload',
  'organization_service',
  '$filter',
  function ($scope,
            all_columns,
            organization_payload,
            query_threshold_payload,
            shared_fields_payload,
            auth_payload,
            organization_service,
            $filter) {
    $scope.fields = all_columns.fields;
    $scope.org = organization_payload.organization;
    $scope.filter_params = {};
    $scope.org.query_threshold = query_threshold_payload.query_threshold;
    $scope.auth = auth_payload.auth;
    $scope.infinite_fields = $scope.fields.slice(0, 20);
    $scope.controls = {
      select_all: false
    };

    $scope.$watch('filter_params.title', function () {
      if (!$scope.filter_params.title) {
        $scope.controls.select_all = false;
      }
    });

    /**
     * updates all the fields checkboxes to match the ``select_all`` checkbox
     */
    $scope.select_all_clicked = function (type) {
      var fields = $filter('filter')($scope.fields, $scope.filter_params);
      fields = fields.map(function (f) {
        return f.sort_column;
      });
      if (type === 'internal') {
        $scope.fields = $scope.fields.map(function (f) {
          if (_.includes(fields, f.sort_column)) {
            f.checked = $scope.controls.select_all;
          }
          return f;
        });
      } else if (type === 'public') {
        $scope.fields = $scope.fields.map(function (f) {
          if (_.includes(fields, f.sort_column)) {
            f.public_checked = $scope.controls.public_select_all;
          }
          return f;
        });
      }
    };

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
      $scope.org.fields = $scope.fields.filter(function (f) {
        return f.checked;
      });
      $scope.org.public_fields = $scope.fields.filter(function (f) {
        return f.public_checked;
      });
      organization_service.save_org_settings($scope.org).then(function () {
        $scope.settings_updated = true;
      }, function (data) {
        $scope.$emit('app_error', data);
      });
    };

    /**
     * preforms from initial data processing:
     * - sets the checked shared fields
     */
    var init = function () {
      var sort_columns = shared_fields_payload.shared_fields.map(function (f) {
        return f.sort_column;
      });
      var public_columns = shared_fields_payload.public_fields.map(function (f) {
        return f.sort_column;
      });
      $scope.fields = $scope.fields.map(function (f) {
        if (_.includes(sort_columns, f.sort_column)) {
          f.checked = true;
        }
        if (_.includes(public_columns, f.sort_column)) {
          f.public_checked = true;
        }
        return f;
      });
    };
    init();

  }]);
