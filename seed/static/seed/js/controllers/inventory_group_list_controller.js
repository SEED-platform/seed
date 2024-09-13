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
      inventory_groups,
      current_inventory_group,
      organization_payload
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory_groups = inventory_groups.sort((a, b) => a.name - b.name);
      $scope.currentInventoryGroup = current_inventory_group;
      $scope.org_id = organization_payload;

      $scope.edit_inventory_group = function (group_id) {
        const selected_group = $scope.inventory_groups.find(g => g.id === group_id);
        const oldGroup = angular.copy(selected_group);
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/inventory_group_modal.html`,
          controller: 'inventory_group_modal_controller',
          resolve: {
            action: _.constant('edit'),
            data: selected_group,
            org_id: () => user_service.get_organization().id,
            inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')
          }
        });

        modalInstance.result.then(() => {
          $state.reload();
          Notification.primary(`Success!`);
        })
      };

      $scope.remove_inventory_group = function (group_id) {
        const selected_group = $scope.inventory_groups.find(g => g.id === group_id);
        const oldGroup = angular.copy(selected_group);
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/inventory_group_modal.html`,
          controller: 'inventory_group_modal_controller',
          resolve: {
            action: _.constant('remove'),
            data: _.constant(selected_group),
            org_id: () => user_service.get_organization().id,
            inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')
          }
        });

        modalInstance.result.then(() => {
          modified_service.resetModified();
          $state.reload(); 
          Notification.primary(`Removed ${oldGroup.name}`);
        });
      };

      $scope.create_inventory_group = function () {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/inventory_group_modal.html`,
          controller: 'inventory_group_modal_controller',
          resolve: {
            action: _.constant('create'),
            data: _.constant(''),
            org_id: () => user_service.get_organization().id,
            inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')
          }
        });

        modalInstance.result.then((newGroup) => {
          $state.reload();
          Notification.primary(`Created ${newGroup.name}`);
        });
      };

      $scope.profile_change = function () {
        inventory_service.save_last_inventory_group($scope.currentInventoryGroup.id, $scope.inventory_type);
      };
      $scope.isModified = () => modified_service.isModified();

      $scope.groupGridOptions = {
        data: 'inventory_groups',
        columnDefs: [
          {
            name: 'id',
            displayName: '',
            headerCellTemplate: '<span></span>', // remove header
            cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <a title="${$translate.instant('Go to Detail Page')}"` +
            '     class="ui-grid-cell-contents" ' +
            '     ui-sref="inventory_group_detail(grid.appScope.inventory_type === \'properties\' ? {inventory_type: \'properties\', group_id: row.entity.id} : {inventory_type: \'taxlots\', group_id: row.entity.id})">' +
            '    <i class="ui-grid-icon-info-circled"></i>' +
            '  </a>' +
            '</div>',
            enableColumnMenu: false,
            enableColumnMoving: false,
            enableColumnResizing: false,
            enableFiltering: false,
            enableHiding: false,
            enableSorting: false,
            exporterSuppressExport: true,
            pinnedLeft: true,
            visible: true,
            width: 30
          },
          { field: 'name' }
        ],
        enableGridMenu: true,
        exporterMenuPdf: false,
        exporterMenuExcel: false,
        enableColumnResizing: true,
        flatEntityAccess: true,
        fastWatch: true,
        gridMenuShowHideColumns: false,
        minRowsToShow: Math.min($scope.inventory_groups.length, 10)
      };
    }]);
