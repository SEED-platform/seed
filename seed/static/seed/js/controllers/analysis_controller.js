/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.analysis', [])
  .controller('analysis_controller', [
    '$scope',
    '$stateParams',
    '$state',
    'analysis_payload',
    'organization_payload',
    'messages_payload',
    'users_payload',
    'views_payload',
    'auth_payload',
    function (
      $scope,
      $stateParams,
      $state,
      analysis_payload,
      organization_payload,
      messages_payload,
      users_payload,
      views_payload,
      auth_payload
    ) {
      // WARNING: $scope.org is used by "child" controller - analysis_details_controller
      $scope.org = organization_payload;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.auth = auth_payload.auth;
      $scope.analysis = analysis_payload.analysis;
      $scope.messages = messages_payload.messages;
      $scope.users = users_payload.users;
      $scope.views = views_payload.views;
      $scope.view_id = $stateParams.view_id;
      $scope.original_views = views_payload.original_views;


      $scope.has_children = function (value) {
        if (typeof value == 'object') {
          return true;
        }
      };
    }]);
