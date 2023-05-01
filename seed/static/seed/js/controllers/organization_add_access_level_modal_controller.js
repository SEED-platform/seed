/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.organization_add_access_level_modal', [])
  .controller('organization_add_access_level_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'organization_service',
    'org_id',
    'current_access_level_names',
    'Notification',
    function (
      $scope,
      $state,
      $uibModalInstance,
      organization_service,
      org_id,
      current_access_level_names,
      Notification,
    ) {
      $scope.current_access_level_names = [...current_access_level_names];
      $scope.new_access_level_names = current_access_level_names;

      $scope.is_modifed = function() {
        return !_.isEqual($scope.current_access_level_names, $scope.new_access_level_names);
      }

      $scope.save_access_level_names = function () {
        organization_service.update_organization_access_level_names(org_id, $scope.new_access_level_names)
        .then(
          _ => $uibModalInstance.close()
        )
        .catch(err => {
          Notification.error(err);
        })
      };

      $scope.add_level = function() {
        $scope.new_access_level_names.push("");
      }
    }]);
