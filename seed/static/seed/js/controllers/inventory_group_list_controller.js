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
      organization_payload,
  ) {
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.inventory_groups = inventory_groups;
    $scope.currentInventoryGroup = current_inventory_group;
    $scope.org_id = organization_payload;

    $scope.rename_inventory_group = function () {
      var oldGroup = angular.copy($scope.currentInventoryGroup);

      var modalInstance = $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/inventory_group_modal.html',
        controller: 'inventory_group_modal_controller',
        resolve: {
          action: _.constant('rename'),
          data: _.constant($scope.currentInventoryGroup),
          org_id: function () {
            return user_service.get_organization().id;
          },
          inventory_type: function () {
            return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
          }
        }
      });

      modalInstance.result.then(function (newName) {
        $scope.currentInventoryGroup.name = newName;
        _.find($scope.inventory_groups, {id: $scope.currentInventoryGroup.id}).name = newName;
        Notification.primary('Renamed ' + oldGroup.name + ' to ' + newName);
      });
    };

    $scope.remove_inventory_group = function () {
      var oldGroup = angular.copy($scope.currentInventoryGroup);
      var modalInstance = $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/inventory_group_modal.html',
        controller: 'inventory_group_modal_controller',
        resolve: {
          action: _.constant('remove'),
          data: _.constant($scope.currentInventoryGroup),
          org_id: function () {
            return user_service.get_organization().id;
          },
          inventory_type: function () {
            return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
          }
        }
      });

      modalInstance.result.then(function () {
        _.remove($scope.inventory_groups, oldGroup);
        modified_service.resetModified();
        $scope.currentInventoryGroup = _.first($scope.inventory_groups);
        Notification.primary('Removed ' + oldGroup.name);
      });
    };

    $scope.new_inventory_group = function () {
      var modalInstance = $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/inventory_group_modal.html',
        controller: 'inventory_group_modal_controller',
        resolve: {
          action: _.constant('new'),
          data: _.constant(""),
          org_id: function () {
            return user_service.get_organization().id;
          },
          inventory_type: function () {
            return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
          }
        }
      });

      modalInstance.result.then(function (newGroup) {
        $scope.inventory_groups.push(newGroup);
        modified_service.resetModified();
        $scope.currentInventoryGroup = _.last($scope.inventory_groups);
        inventory_service.save_last_inventory_group(newGroup.id, $scope.inventory_type);
        Notification.primary('Created ' + newGroup.name);
      });
    };

    $scope.profile_change = function () {
      inventory_service.save_last_inventory_group($scope.currentInventoryGroup.id, $scope.inventory_type);
    };
    $scope.isModified = function () {
      return modified_service.isModified();
    };

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
            `     class="ui-grid-cell-contents" ` +
            `     ui-sref="inventory_group_detail(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'properties', group_id: row.entity.id} : {inventory_type: 'taxlots', group_id: row.entity.id})">` +
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
        { field: 'name' },
      ],
      enableGridMenu: true,
      exporterMenuPdf: false,
      exporterMenuExcel: false,
      enableColumnResizing: true,
      flatEntityAccess: true,
      fastWatch: true,
      gridMenuShowHideColumns: false,
      minRowsToShow: Math.min($scope.inventory_groups.length, 10),
    };
  }]);
