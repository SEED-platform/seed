/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_notes_modal', []).controller('inventory_detail_notes_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'action',
  'note_service',
  'inventoryType',
  'viewId',
  'note',
  'orgId',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, action, note_service, inventoryType, viewId, note, orgId) {
    $scope.inventoryType = inventoryType;
    $scope.viewId = viewId;
    $scope.orgId = orgId;
    $scope.action = action;
    $scope.note = angular.copy(note);

    $scope.close = () => {
      $uibModalInstance.dismiss();
    };

    $scope.create = () => {
      const data = {
        name: 'Manually Created',
        note_type: 'Note',
        text: $scope.note.text
      };
      note_service.create_note($scope.orgId, $scope.inventoryType, $scope.viewId, data).then(() => {
        $uibModalInstance.close();
      });
    };

    $scope.update = () => {
      const data = {
        name: $scope.note.name,
        note_type: $scope.note.note_type,
        text: $scope.note.text
      };
      note_service.update_note($scope.orgId, $scope.inventoryType, $scope.viewId, $scope.note.id, data).then(() => {
        $uibModalInstance.close();
      });
    };

    $scope.delete = () => {
      note_service.delete_note($scope.inventoryType, $scope.viewId, $scope.note.id).then(() => {
        $uibModalInstance.close();
      });
    };
  }
]);
