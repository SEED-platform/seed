/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_notes_modal', [])
  .controller('inventory_detail_notes_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'action',
    'note_service',
    'inventoryType',
    'viewId',
    'note',
    'orgId',
    function (
      $scope,
      $uibModalInstance,
      action,
      note_service,
      inventoryType,
      viewId,
      note,
      orgId
    ) {
      $scope.inventoryType = inventoryType;
      $scope.viewId = viewId;
      $scope.orgId = orgId;
      $scope.action = action;
      $scope.note = angular.copy(note);

      $scope.close = function () {
        $uibModalInstance.dismiss();
      };

      $scope.create = function () {
        var data = {
          name: 'Manually Created',
          note_type: 'Note',
          text: $scope.note.text
        };
        note_service.create_note($scope.orgId, $scope.inventoryType, $scope.viewId, data).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.update = function () {
        var data = {
          name: $scope.note.name,
          note_type: $scope.note.note_type,
          text: $scope.note.text
        };
        note_service.update_note($scope.orgId, $scope.inventoryType, $scope.viewId, $scope.note.id, data).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.delete = function () {
        note_service.delete_note($scope.inventoryType, $scope.viewId, $scope.note.id).then(function () {
          $uibModalInstance.close();
        });
      };
    }]);
