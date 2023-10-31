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
      spinner_utility
    ) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
      $scope.access_level_tree = access_level_tree.access_level_tree;
      $scope.access_level_names = access_level_tree.access_level_names;

      $scope.accordionsCollapsed = true;
      $scope.collapseAccordions = (collapseAll) => {
        $scope.accordionsCollapsed = collapseAll;
        const action = collapseAll ? 'hide' : 'show';
        $('.level-collapse').collapse(action);
      };

      $scope.open_add_level_modal = function () {
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/organization_add_access_level_modal.html`,
          controller: 'organization_add_access_level_modal_controller',
          resolve: {
            org_id: () => $scope.org.id,
            current_access_level_names: () => $scope.access_level_names
          }
        }).result.then(() => {
          spinner_utility.show();
          $window.location.reload();
        });
      };

      $scope.open_add_level_instance_modal = function () {
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/organization_add_access_level_instance_modal.html`,
          controller: 'organization_add_access_level_instance_modal_controller',
          resolve: {
            org_id: () => $scope.org.id,
            level_names: () => $scope.access_level_names,
            access_level_tree: () => $scope.access_level_tree
          }
        }).result.then(() => {
          spinner_utility.show();
          $window.location.reload();
        });
      };

      $scope.open_upload_al_instances_modal = function () {
        const step = 20; // this is the step that corresponds to uploading access levels
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/data_upload_modal.html`,
          controller: 'data_upload_modal_controller',
          resolve: {
            cycles: () => [],
            step: () => step,
            dataset: () => null,
            organization: () => $scope.menu.user.organization
          }
        }).result.finally(() => {
          $window.location.reload();
        });
      };

      $scope.open_delete_al_instance_modal = function(instance_id, instance_name) {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/organization_delete_access_level_instance_modal.html',
          controller: 'organization_delete_access_level_instance_modal_controller',
          resolve: {
            org_id: function() {return $scope.org.id},
            instance_id: function() {return instance_id},
            instance_name: function() {return instance_name}
          },
        }).result.then(function () {
          spinner_utility.show();
          $window.location.reload();
        });
      };

      $scope.open_delete_al_instance_modal = (instance_id, instance_name) => {
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/organization_edit_access_level_instance_modal.html`,
          controller: 'organization_delete_access_level_instance_modal_controller',
          resolve: {
            org_id: () => $scope.org.id,
            instance_id: () => instance_id,
            instance_name: () => instance_name
          }
        }).result.then(() => {
          spinner_utility.show();
          $window.location.reload();
        });
      };

      $scope.open_edit_al_instance_modal = function (instance_id, instance_name) {
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/organization_edit_access_level_instance_modal.html`,
          controller: 'organization_edit_access_level_instance_modal_controller',
          resolve: {
            org_id: () => $scope.org.id,
            instance_id: () => instance_id,
            instance_name: () => instance_name
          }
        }).result.then(() => {
          spinner_utility.show();
          $window.location.reload();
        });
      };
    }
  ]);
