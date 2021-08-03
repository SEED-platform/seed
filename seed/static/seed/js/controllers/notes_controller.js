/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.notes', [])
  .controller('notes_controller', [
    '$scope',
    '$uibModalInstance',
    'urls',
    'note_service',
    'inventory_type',
    'view_id',
    'inventory_payload',
    'organization_payload',
    'notes',
    function ($scope, $uibModalInstance, urls, note_service, inventory_type, view_id, inventory_payload, organization_payload, notes) {
      $scope.inventory_type = inventory_type;
      $scope.notes = notes;
      $scope.org_id = organization_payload.organization.org_id;
      $scope.urls = urls;

      $scope.inventory_name = note_service.inventory_display_name(inventory_type === 'properties' ? 'property' : 'taxlot', organization_payload.organization, inventory_payload.state);

      $scope.close = function () {
        if ($uibModalInstance) {
          $uibModalInstance.close($scope.notes.length);
        }
      };

      $scope.open_create_note_modal = function () {
        note_service.open_create_note_modal($scope.inventory_type, $scope.org_id, view_id).then(function (notes) {
          $scope.notes = notes;
        });
      }

      $scope.open_edit_note_modal = function (note) {
        note_service.open_edit_note_modal($scope.inventory_type, $scope.org_id, view_id, note).then(function (notes) {
          $scope.notes = notes;
        });
      }

      $scope.open_delete_note_modal = function (note) {
        note_service.open_delete_note_modal($scope.inventory_type, $scope.org_id, view_id, note).then(function (notes) {
          $scope.notes = notes;
        });
      }
    }]);
