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
    '$translate',
    'Notification',
    'modified_service',
    'inventory_service',
    'user_service',
    'urls',
    'access_level_tree',
    'inventory_groups',
    'current_inventory_group',
    'organization_payload',
    function (
      $scope,
      $state,
      $stateParams,
      $uibModal,
      $translate,
      Notification,
      modified_service,
      inventory_service,
      user_service,
      urls,
      access_level_tree,
      inventory_groups,
      current_inventory_group,
      organization_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory_groups = inventory_groups;
      $scope.currentInventoryGroup = current_inventory_group;
      $scope.org_id = organization_payload;

      $scope.edit_inventory_group = function (group_id) {
        const selected_group = $scope.inventory_groups.find(g => g.id === group_id);
        const modalInstance = $scope.open_inventory_group_modal('edit', selected_group)

        modalInstance.result.then(() => {
          $state.reload();
          Notification.primary(`Success!`);
        })
      };

      $scope.remove_inventory_group = function (group_id) {
        const selected_group = $scope.inventory_groups.find(g => g.id === group_id);
        const oldGroup = angular.copy(selected_group);
        const modalInstance = $scope.open_inventory_group_modal('remove', selected_group)

        modalInstance.result.then(() => {
          modified_service.resetModified();
          $state.reload();
          Notification.primary(`Removed ${oldGroup.name}`);
        });
      };

      $scope.create_inventory_group = function () {
        const modalInstance = $scope.open_inventory_group_modal('create', "")

        modalInstance.result.then((newGroup) => {
          $state.reload();
          Notification.primary(`Created ${newGroup.name}`);
        });
      };

      $scope.open_inventory_group_modal = (action, data) => {
        return $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/inventory_group_modal.html`,
          controller: 'inventory_group_modal_controller',
          resolve: {
            access_level_tree: () => access_level_tree,
            action: _.constant(action),
            data: _.constant(data),
            inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot'),
            org_id: () => user_service.get_organization().id
          }
        });

      }

      $scope.profile_change = function () {
        inventory_service.save_last_inventory_group($scope.currentInventoryGroup.id, $scope.inventory_type);
      };
      $scope.isModified = () => modified_service.isModified();

    }]);
