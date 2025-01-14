/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_list', [])
  .controller('inventory_group_list_controller', [
    '$scope',
    '$state',
    '$stateParams',
    '$uibModal',
    'Notification',
    'modified_service',
    'inventory_service',
    'user_service',
    'urls',
    'access_level_tree',
    'inventory_groups',
    'current_inventory_group',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      $uibModal,
      Notification,
      modified_service,
      inventory_service,
      user_service,
      urls,
      access_level_tree,
      inventory_groups,
      current_inventory_group
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory_groups = inventory_groups;
      $scope.currentInventoryGroup = current_inventory_group;
      $scope.org = user_service.get_organization();

      $scope.edit_inventory_group = (group_id) => {
        const selected_group = $scope.inventory_groups.find((g) => g.id === group_id);
        const modalInstance = $scope.open_inventory_group_modal('edit', selected_group);

        modalInstance.result.then(() => {
          $state.reload();
          Notification.primary('Success!');
        });
      };

      $scope.remove_inventory_group = (group_id) => {
        const selected_group = $scope.inventory_groups.find((g) => g.id === group_id);
        const oldGroup = angular.copy(selected_group);
        const modalInstance = $scope.open_inventory_group_modal('remove', selected_group);

        modalInstance.result.then(() => {
          modified_service.resetModified();
          $state.reload();
          Notification.primary(`Removed ${oldGroup.name}`);
        });
      };

      $scope.create_inventory_group = () => {
        const modalInstance = $scope.open_inventory_group_modal('create', '');

        modalInstance.result.then((newGroup) => {
          $state.reload();
          Notification.primary(`Created ${newGroup.name}`);
        });
      };

      $scope.open_inventory_group_modal = (action, data) => $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/inventory_group_modal.html`,
        controller: 'inventory_group_modal_controller',
        resolve: {
          access_level_tree: () => access_level_tree,
          action: _.constant(action),
          data: _.constant(data),
          inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot'),
          org_id: () => $scope.org.id
        }
      });

      $scope.profile_change = () => {
        inventory_service.save_last_inventory_group($scope.currentInventoryGroup.id, $scope.inventory_type);
      };
      $scope.isModified = () => modified_service.isModified();
    }]);
