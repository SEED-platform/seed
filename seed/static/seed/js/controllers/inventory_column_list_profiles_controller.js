/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_column_list_profiles', []).controller('inventory_column_list_profiles_controller', [
  '$scope',
  '$window',
  '$uibModalInstance',
  '$stateParams',
  '$uibModal',
  'Notification',
  'inventory_service',
  'modified_service',
  'user_service',
  'urls',
  'all_columns',
  'profiles',
  'current_profile',
  'shared_fields_payload',
  '$translate',
  'i18nService',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $window,
    $uibModalInstance,
    $stateParams,
    $uibModal,
    Notification,
    inventory_service,
    modified_service,
    user_service,
    urls,
    all_columns,
    profiles,
    current_profile,
    shared_fields_payload,
    $translate,
    i18nService
  ) {
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.inventory = {
      id: $stateParams.inventory_id
    };
    $scope.cycle = {
      id: $stateParams.cycle_id
    };

    $scope.profiles = profiles;
    $scope.currentProfile = current_profile;

    $scope.gridOptions = {
      enableColumnMenus: false,
      enableFiltering: true,
      enableGridMenu: true,
      enableSorting: false,
      flatEntityAccess: true,
      gridMenuShowHideColumns: false,
      minRowsToShow: 30,
      rowTemplate:
        '<div grid="grid" class="ui-grid-draggable-row" ng-attr-draggable="{$ grid.appScope.menu.user.organization.user_role !== \'viewer\' $}"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
      columnDefs: [
        {
          name: 'pinnedLeft',
          displayName: '',
          cellTemplate:
            '<div class="ui-grid-row-header-link" ng-if="!row.entity.is_derived_column">' +
            '  <a class="ui-grid-cell-contents pinnable" style="text-align: center;" ng-disabled="!COL_FIELD" ng-click="grid.appScope.menu.user.organization.user_role !== \'viewer\' && grid.appScope.togglePinned(row)">' +
            '    <i class="fa fa-thumb-tack"></i>' +
            '  </a>' +
            '</div>',
          enableColumnMenu: false,
          enableFiltering: false,
          enableSorting: false,
          width: 30
        },
        {
          name: 'displayName',
          displayName: 'Column Name',
          headerCellFilter: 'translate',
          cellFilter: 'translate',
          cellTemplate:
            '<div class="ui-grid-cell-contents inventory-settings-cell" title="TOOLTIP" data-after-content="{$ row.entity.column_name $}"> <i ng-if="row.entity.derived_column" class="fa fa-link" style="margin-right: 10px;"></i>{$ COL_FIELD CUSTOM_FILTERS $} <span ng-if="row.entity.related" class="badge" style="margin-left: 10px;">{$ grid.appScope.inventory_type === "properties" ? ("tax lot" | translate) : ("property" | translate) $}</span></div>',
          enableHiding: false
        }
      ],
      onRegisterApi(gridApi) {
        $scope.gridApi = gridApi;
        initializeRowSelections();

        gridApi.selection.on.rowSelectionChanged($scope, rowSelectionChanged);
        gridApi.selection.on.rowSelectionChangedBatch($scope, rowSelectionChanged);
        gridApi.dragndrop.setDragDisabled($scope.menu.user.organization.user_role === 'viewer');
        gridApi.draggableRows.on.rowDropped($scope, modified_service.setModified);

        _.delay($scope.updateHeight, 150);
        const debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
        angular.element($window).on('resize', debouncedHeightUpdate);
        $scope.$on('$destroy', () => {
          angular.element($window).off('resize', debouncedHeightUpdate);
        });
      }
    };

    const initializeRowSelections = () => {
      $scope.gridApi.grid.modifyRows($scope.gridOptions.data);
      _.forEach($scope.gridApi.grid.rows, (row) => {
        if (row.entity.visible !== false) {
          row.setSelected(true);
        }
        if ($scope.menu.user.organization.user_role === 'viewer') {
          row.enableSelection = false;
        }
      });
    };

    const setColumnsForCurrentProfile = () => {
      const deselected_columns = angular.copy(all_columns);
      if ($scope.currentProfile) {
        const profileColumns = _.filter($scope.currentProfile.columns, (col) => _.find(angular.copy(all_columns), { id: col.id }));

        $scope.gridOptions.data = _.map(profileColumns, (col) => {
          const c = _.remove(deselected_columns, { id: col.id })[0];
          c.pinnedLeft = col.pinned;
          c.visible = true;
          return c;
        }).concat(
          _.map(deselected_columns, (col) => {
            col.pinnedLeft = false;
            col.visible = false;
            return col;
          })
        );

        $scope.gridOptions.data = inventory_service.reorderSettings($scope.gridOptions.data);
      } else {
        // No profiles exist
        const data = _.map(deselected_columns, (col) => {
          col.visible = !col.is_extra_data;
          return col;
        });
        $scope.gridOptions.data = inventory_service.reorderSettings(data);
      }
    };
    setColumnsForCurrentProfile();

    let ignoreNextChange = true;
    $scope.$watch('currentProfile', (newProfile, oldProfile) => {
      if (ignoreNextChange) {
        ignoreNextChange = false;
        return;
      }

      if (!modified_service.isModified()) {
        switchProfile(newProfile);
      } else {
        $uibModal
          .open({
            template:
              '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch profiles without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch Profiles</button></div>'
          })
          .result.then(() => {
            modified_service.resetModified();
            switchProfile(newProfile);
          })
          .catch(() => {
            ignoreNextChange = true;
            $scope.currentProfile = oldProfile;
          });
      }
    });

    function switchProfile(newProfile) {
      ignoreNextChange = true;
      if (newProfile) {
        $scope.currentProfile = _.find($scope.profiles, { id: newProfile.id });
        inventory_service.save_last_profile(newProfile.id, $scope.inventory_type);
      } else {
        $scope.currentProfile = undefined;
      }

      setColumnsForCurrentProfile();
      initializeRowSelections();
    }

    // set up i18n
    //
    // let angular-translate be in charge ... need
    // to feed the language-only part of its $translate setting into
    // ui-grid's i18nService
    const stripRegion = (languageTag) => _.first(languageTag.split('_'));
    i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

    $scope.showSharedBuildings = shared_fields_payload.show_shared_buildings;

    const rowSelectionChanged = () => {
      _.forEach($scope.gridApi.grid.rows, (row) => {
        row.entity.visible = row.isSelected;
        if (!row.isSelected && row.entity.pinnedLeft) row.entity.pinnedLeft = false;
      });
      $scope.gridOptions.data = inventory_service.reorderSettings($scope.gridOptions.data);
      modified_service.setModified();
    };

    $scope.updateHeight = () => {
      let height = 0;
      _.forEach(['.header', '.page_header_container', '.section_nav_container', '.section_header_container', '.section_content.with_padding'], (selector) => {
        const element = angular.element(selector)[0];
        if (element) height += element.offsetHeight;
      });
      angular.element('#grid-container').css('height', `calc(100vh - ${height}px)`);
      angular.element('#grid-container > div').css('height', `calc(100vh - ${height + 2}px)`);
      $scope.gridApi.core.handleWindowResize();
    };

    const currentColumns = () => {
      const columns = [];
      _.forEach($scope.gridApi.grid.rows, (row) => {
        if (row.isSelected) {
          columns.push({
            column_name: row.entity.column_name,
            id: row.entity.id,
            order: columns.length + 1,
            pinned: Boolean(row.entity.pinnedLeft),
            table_name: row.entity.table_name,
            derived_column: row.entity.derived_column
          });
        }
      });
      return columns;
    };

    $scope.saveProfile = () => {
      const { id } = $scope.currentProfile;
      const profile = _.omit($scope.currentProfile, 'id');
      profile.columns = currentColumns();
      inventory_service.update_column_list_profile(id, profile).then((updatedProfile) => {
        const index = _.findIndex($scope.profiles, { id: updatedProfile.id });
        $scope.profiles[index] = updatedProfile;
        modified_service.resetModified();
        Notification.primary(`Saved ${$scope.currentProfile.name}`);
      });
    };

    $scope.renameProfile = () => {
      const oldProfile = angular.copy($scope.currentProfile);

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/settings_profile_modal.html`,
        controller: 'settings_profile_modal_controller',
        resolve: {
          action: () => 'rename',
          data: () => $scope.currentProfile,
          profile_location: () => 'List View Profile',
          inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')
        }
      });

      modalInstance.result.then((newName) => {
        $scope.currentProfile.name = newName;
        _.find($scope.profiles, { id: $scope.currentProfile.id }).name = newName;
        Notification.primary(`Renamed ${oldProfile.name} to ${newName}`);
      });
    };

    $scope.removeProfile = () => {
      const oldProfile = angular.copy($scope.currentProfile);

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/settings_profile_modal.html`,
        controller: 'settings_profile_modal_controller',
        resolve: {
          action: () => 'remove',
          data: () => $scope.currentProfile,
          profile_location: () => 'List View Profile',
          inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')
        }
      });

      modalInstance.result.then(() => {
        _.remove($scope.profiles, oldProfile);
        modified_service.resetModified();
        $scope.currentProfile = _.first($scope.profiles);
        Notification.primary(`Removed ${oldProfile.name}`);
      });
    };

    $scope.newProfile = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/settings_profile_modal.html`,
        controller: 'settings_profile_modal_controller',
        resolve: {
          action: () => 'new',
          data: {
            columns: currentColumns(),
            derived_columns: []
          },
          profile_location: () => 'List View Profile',
          inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')
        }
      });

      modalInstance.result.then((newProfile) => {
        $scope.profiles.push(newProfile);
        modified_service.resetModified();
        $scope.currentProfile = _.last($scope.profiles);
        Notification.primary(`Created ${newProfile.name}`);
      });
    };

    $scope.isModified = () => modified_service.isModified();

    $scope.togglePinned = (row) => {
      row.entity.pinnedLeft = !row.entity.pinnedLeft;
      if (row.entity.pinnedLeft) {
        row.entity.visible = true;
        row.setSelected(true);
      }
      $scope.gridOptions.data = inventory_service.reorderSettings($scope.gridOptions.data);
      modified_service.setModified();
    };
  }
]);