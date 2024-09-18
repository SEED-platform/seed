/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.notes', []).controller('notes_controller', [
  '$scope',
  '$uibModalInstance',
  'urls',
  'note_service',
  'organization_service',
  'inventory_type',
  'view_id',
  'inventory_payload',
  'organization_payload',
  'notes',
  'auth_payload',
  // eslint-disable-next-line func-names
  function ($scope, $uibModalInstance, urls, note_service, organization_service, inventory_type, view_id, inventory_payload, organization_payload, notes, auth_payload) {
    $scope.inventory_type = inventory_type;
    const item_state = inventory_payload.state;
    $scope.notes = notes;
    $scope.organization = organization_payload.organization;
    $scope.urls = urls;
    $scope.auth = auth_payload.auth;

    $scope.inventory_display_name = organization_service.get_inventory_display_value($scope.organization, $scope.inventory_type === 'properties' ? 'property' : 'taxlot', item_state);

    $scope.inventory = { view_id };

    $scope.close = () => {
      if ($uibModalInstance) {
        $uibModalInstance.close($scope.notes.length);
      }
    };

    $scope.open_create_note_modal = () => {
      note_service.open_create_note_modal($scope.inventory_type, $scope.organization.id, view_id).then((notes) => {
        $scope.notes = notes;
      });
    };

    $scope.open_edit_note_modal = (note) => {
      note_service.open_edit_note_modal($scope.inventory_type, $scope.organization.id, view_id, note).then((notes) => {
        $scope.notes = notes;
      });
    };

    $scope.open_delete_note_modal = (note) => {
      note_service.open_delete_note_modal($scope.inventory_type, $scope.organization.id, view_id, note).then((notes) => {
        $scope.notes = notes;
      });
    };
  }
]);
