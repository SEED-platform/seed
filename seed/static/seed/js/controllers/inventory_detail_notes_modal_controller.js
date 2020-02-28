/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
      $scope.note = note;

      $scope.close = function () {
        $uibModalInstance.dismiss();
      };

      $scope.create = function () {
        var data = {
          name: 'Manually Created',
          note_type: 'Note',
          text: note.text,
        };
        note_service.create_note($scope.orgId, $scope.inventoryType, $scope.viewId, data).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.update = function () {
        var data = {
          name: note.name,
          note_type: note.note_type,
          text: note.text,
        };
        note_service.update_note($scope.orgId, $scope.inventoryType, $scope.viewId, note.id, data).then(function () {
          $uibModalInstance.close();
        });
      };

      $scope.delete = function () {
        note_service.delete_note($scope.inventoryType, $scope.viewId, note.id).then(function () {
          $uibModalInstance.close();
        });
      };
    }]);
