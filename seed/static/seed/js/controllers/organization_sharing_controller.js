/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
  // eslint-disable-next-line func-names
  function ($scope, all_columns, organization_payload, query_threshold_payload, shared_fields_payload, auth_payload, organization_service, $filter) {
    $scope.fields = all_columns.columns;
    $scope.org = organization_payload.organization;
    $scope.filter_params = {};
    $scope.org.query_threshold = query_threshold_payload.query_threshold;
    $scope.auth = auth_payload.auth;
    $scope.infinite_fields = $scope.fields.slice(0, 20);
    $scope.controls = {
      select_all: false
    };

    $scope.$watch('filter_params.title', () => {
      if (!$scope.filter_params.title) {
        $scope.controls.select_all = false;
      }
    });

    /**
     * updates all the fields checkboxes to match the ``select_all`` checkbox
     */
    $scope.select_all_clicked = (type) => {
      let fields = $filter('filter')($scope.fields, $scope.filter_params);
      fields = fields.map((f) => f.name);
      if (type === 'public') {
        $scope.fields = $scope.fields.map((f) => {
          if (fields.includes(f.name)) {
            f.public_checked = $scope.controls.public_select_all;
          }
          return f;
        });
      }
    };

    /**
     * saves the updates settings
     */
    $scope.save_settings = () => {
      $scope.org.public_fields = $scope.fields.filter((f) => f.public_checked);
      organization_service.save_org_settings($scope.org).then(
        () => {
          $scope.settings_updated = true;
        },
        (data) => {
          $scope.$emit('app_error', data);
        }
      );
    };

    /**
     * preforms from initial data processing:
     * - sets the checked shared fields
     */
    const init = () => {
      const public_columns = shared_fields_payload.public_fields.map((f) => f.name);
      $scope.fields = $scope.fields.map((f) => {
        if (public_columns.includes(f.name)) {
          f.public_checked = true;
        }
        return f;
      });
    };
    init();
  }
]);
