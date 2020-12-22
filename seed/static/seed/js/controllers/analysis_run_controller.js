/*
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.analysis_run', [])
  .controller('analysis_run_controller', [
    '$scope',
    '$stateParams',
    '$state',
    'analysis_payload',
    'organization_payload',
    'messages_payload',
    'users_payload',
    'view_payload',
    'auth_payload',
    'urls',
    function (
      $scope,
      $stateParams,
      $state,
      analysis_payload,
      organization_payload,
      messages_payload,
      users_payload,
      view_payload,
      auth_payload,
      urls
    ) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
      $scope.analysis = analysis_payload.analysis;
      $scope.messages = messages_payload.messages;
      $scope.users = users_payload.users;
      // Forces analysis_runs.html to only show one view/run - the selected run
      $scope.views = [view_payload.view];
      $scope.view = view_payload.view;
      $scope.view_id = $stateParams.view_id;
}]);
