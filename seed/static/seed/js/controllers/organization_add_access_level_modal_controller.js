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
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      organization_service,
      org_id,
      current_access_level_names,
      Notification
    ) {
      $scope.new_access_level_names = angular.copy(current_access_level_names);

      $scope.is_modified = () => !_.isEqual(current_access_level_names, $scope.new_access_level_names);

      $scope.save_access_level_names = () => {
        organization_service.update_organization_access_level_names(org_id, $scope.new_access_level_names)
          .then(() => $uibModalInstance.close())
          .catch((err) => {
            console.log(err.data.message);
            Notification.error(err.data.message);
          });
      };

      $scope.remove_level = () => {
        $scope.new_access_level_names.pop();
      };

      $scope.add_level = () => {
        $scope.new_access_level_names.push('');
      };

      $scope.cancel = () => {
        $uibModalInstance.dismiss('cancel');
      };
    }]);
