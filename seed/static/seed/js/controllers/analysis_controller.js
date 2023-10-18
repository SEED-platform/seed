/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */

angular.module('BE.seed.controller.analysis', []).controller('analysis_controller', [
  '$scope',
  '$stateParams',
  '$state',
  'organization_service',
  'analysis_payload',
  'organization_payload',
  'messages_payload',
  'users_payload',
  'views_payload',
  'auth_payload',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, $state, organization_service, analysis_payload, organization_payload, messages_payload, users_payload, views_payload, auth_payload) {
    // WARNING: $scope.org is used by "child" controller - analysis_details_controller
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
    $scope.analysis = analysis_payload.analysis;
    $scope.messages = messages_payload.messages;
    $scope.users = users_payload.users;
    $scope.views = views_payload.views;
    $scope.view_id = $stateParams.view_id;
    $scope.original_views = views_payload.original_views;

    $scope.has_children = (value) => typeof value === 'object';

    $scope.get_display_name = (inventory_state) => organization_service.get_inventory_display_value(
      $scope.org,
      // NOTE: hardcoding 'property' b/c you can only run analyses on properties
      'property',
      inventory_state
    );
  }
]);
