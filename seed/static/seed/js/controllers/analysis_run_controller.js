/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */

angular.module('BE.seed.controller.analysis_run', []).controller('analysis_run_controller', [
  '$scope',
  '$stateParams',
  '$state',
  'analysis_payload',
  'organization_payload',
  'messages_payload',
  'users_payload',
  'view_payload',
  'auth_payload',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, $state, analysis_payload, organization_payload, messages_payload, users_payload, view_payload, auth_payload) {
    // WARNING: $scope.org is used by "child" controller - analysis_details_controller
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
    $scope.analysis = analysis_payload.analysis;
    $scope.messages = messages_payload.messages;
    $scope.users = users_payload.users;
    // Forces analysis_runs.html to only show one view/run - the selected run
    $scope.views = [view_payload.view];
    $scope.view = view_payload.view;
    if ($scope.analysis.service === 'BETTER') {
      // for BETTER, make sure we show the Building report before the Portfolio report
      $scope.view.output_files.sort((a) => (a.file.includes('portfolio') ? 1 : -1));
    }
    $scope.view_id = view_payload.view.id;
    $scope.original_view = view_payload.original_view;
    $scope.original_views = {};
    $scope.original_views[view_payload.view.id] = view_payload.original_view;

    $scope.has_children = (value) => typeof value === 'object';
  }
]);
