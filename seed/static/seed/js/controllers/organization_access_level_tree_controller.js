/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization_access_level_tree', [])
  .controller('organization_access_level_tree_controller', [
    '$scope',
    '$uibModal',
    'organization_payload',
    'auth_payload',
    'access_level_tree',
    'urls',
    '$window',
    'spinner_utility',
    function (
      $scope,
      $uibModal,
      organization_payload,
      auth_payload,
      access_level_tree,
      urls,
      $window,
      spinner_utility,
    ) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
      $scope.access_level_tree = access_level_tree.access_level_tree;
      $scope.access_level_names = access_level_tree.access_level_names;

      $scope.open_add_level_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/organization_add_access_level_modal.html',
          controller: 'organization_add_access_level_modal_controller',
          resolve: {
            org_id: function() {return $scope.org.id},
            current_access_level_names: function() {return $scope.access_level_names},
          },
        }).result.then(function () {
          spinner_utility.show();
          $window.location.reload();
        })
      };

      $scope.open_add_level_instance_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/organization_add_access_level_instance_modal.html',
          controller: 'organization_add_access_level_instance_modal_controller',
          resolve: {
            org_id: function() {return $scope.org.id},
            level_names: function() {return $scope.access_level_names},
            access_level_tree: function() {return $scope.access_level_tree},
          },
        }).result.then(function () {
          spinner_utility.show();
          $window.location.reload();
        })
      };
    }
  ]);
