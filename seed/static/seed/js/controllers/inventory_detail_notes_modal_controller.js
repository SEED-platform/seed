/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_notes_modal', [])
  .controller('inventory_detail_notes_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'note_service',
    'inventoryType',
    'inventoryId',
    'orgId',
    function ($scope,
              $uibModalInstance,
              note_service,
              inventoryType,
              inventoryId,
              orgId) {
      $scope.inventoryType = inventoryType;
      $scope.newNote = '';
      $scope.inventoryId = inventoryId;
      $scope.orgId = orgId;

      $scope.close = function () {
        $uibModalInstance.dismiss();
      };

      $scope.save = function () {
        //note_factory.create_note = function (org_id, inventory_type, inventory_id, note_data) {
        var data = {
          name: 'Manually Created',
          note_type: 'Note',
          text: $scope.newNote
        };
        note_service.create_note($scope.orgId, $scope.inventoryType, $scope.inventoryId, data).then(function () {
          $uibModalInstance.close();
        });
      };
    }]);
