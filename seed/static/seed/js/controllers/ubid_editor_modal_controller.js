/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_editor_modal', [])
  .controller('ubid_editor_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'ubid',
    'ubids',
    'state_id',
    'view_id',
    'inventory_key',
    'ubid_service',
    (
      $scope,
      $uibModalInstance,
      ubid,
      ubids,
      state_id,
      view_id,
      inventory_key,
      ubid_service
    ) => {
      $scope.ubid = angular.copy(ubid);
      $scope.state_id = state_id;
      $scope.inventory_key = inventory_key;

      if (!ubid) {
        $scope.ubid = {
          ubid: '',
          preferred: false
        };
        $scope.ubid[inventory_key] = state_id;
        $scope.update = false;
      } else {
        $scope.update = true;
      }

      const already_exists = () => {
        // If creating, check for matching ubids. If updating, exclude the current ubid (id)
        return ubids.find(ubid => ubid.ubid === $scope.ubid.ubid && ubid.id !== $scope.ubid.id);
      };

      $scope.is_valid = () => {
        const invalid = !ubid_service.validate_ubid_js($scope.ubid.ubid);
        const exists = already_exists();

        $scope.invalid = invalid || exists;
        if (invalid) $scope.ubid_error = 'Invalid UBID';
        else if (exists) $scope.ubid_error = 'UBID already exists';

        return !$scope.invalid;
      };

      if ($scope.update) {
        // Check if the pre-existing UBID is valid
        $scope.is_valid();
      }

      $scope.toggle_preferred = () => {
        $scope.ubid.preferred = !$scope.ubid.preferred;
      };

      $scope.upsert_ubid = () => {
        if (!$scope.is_valid()) return;

        $scope.ubid.id ? update_ubid() : create_ubid();
      };

      const create_ubid = async () => {
        await ubid_service.create_ubid(inventory_key, state_id, $scope.ubid);
        $uibModalInstance.close();
      };

      const update_ubid = async () => {
        let ubidsToUpdate = [$scope.ubid];

        if ($scope.ubid.preferred) {
          const preferred_ubids = ubids.filter(ubid => ubid.preferred && ubid.id !== $scope.ubid.id);
          preferred_ubids.forEach(ubid => ubid.preferred = false);
          ubidsToUpdate = [...ubidsToUpdate, ...preferred_ubids];
        }

        const promises = ubidsToUpdate.map(ubid => ubid_service.update_ubid(ubid));
        await Promise.all(promises);
        $uibModalInstance.close();
      };

      $scope.dismiss = () => $uibModalInstance.dismiss();
    }
  ]);
