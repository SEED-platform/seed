/*
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.inventory_detail_analysis_run', [])
  .controller('inventory_detail_analysis_run_controller', [
    '$scope',
    '$stateParams',
    'analysis_payload',
    'inventory_payload',
    'organization_payload',
    'messages_payload',
    'users_payload',
    'view_payload',
    'auth_payload',
    'urls',
    function (
      $scope,
      $stateParams,
      analysis_payload,
      inventory_payload,
      organization_payload,
      messages_payload,
      users_payload,
      view_payload,
      auth_payload,
      urls
    ) {
      $scope.org = organization_payload.organization;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.item_state = inventory_payload.state;
      $scope.auth = auth_payload.auth;
      $scope.analysis = analysis_payload.analysis;
      $scope.messages = messages_payload.messages;
      $scope.users = users_payload.users;
      $scope.views = [view_payload.view];
      $scope.view = view_payload.view;
      $scope.view_id = $stateParams.view_id;
      $scope.inventory = {
        view_id: $stateParams.view_id
      };
}]);
