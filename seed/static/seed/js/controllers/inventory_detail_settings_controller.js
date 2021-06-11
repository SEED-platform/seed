/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_settings', [])
  .controller('inventory_detail_settings_controller', [
    '$scope',
    '$window',
    '$stateParams',
    '$uibModal',
    'Notification',
    'inventory_service',
    'modified_service',
    'user_service',
    'urls',
    'columns',
    'derived_columns_payload',
    'profiles',
    'current_profile',
    '$translate',
    'i18nService', // from ui-grid
    function (
      $scope,
      $window,
      $stateParams,
      $uibModal,
      Notification,
      inventory_service,
      modified_service,
      user_service,
      urls,
      columns,
      derived_columns_payload,
      profiles,
      current_profile,
      $translate,
      i18nService
    ) {

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        view_id: $stateParams.view_id
      };
      $scope.cycle = {
        id: $stateParams.cycle_id
      };

      $scope.profiles = profiles;
      $scope.currentProfile = current_profile;

      const derived_columns = derived_columns_payload.derived_columns;

      var initializeRowSelections = function () {
        if ($scope.gridApi) {
          _.delay(function () {
            $scope.$apply(function () {
              _.forEach($scope.gridApi.grid.rows, function (row) {
                if (row.entity.visible === false) row.setSelected(false);
                else row.setSelected(true);
              });
            });
          });
        }
      };

      var setColumnsForCurrentProfile = function () {
        var deselected_columns = columns.slice();
        var deselected_derived_columns = derived_columns.slice();
        if ($scope.currentProfile) {
          var profileColumns = _.filter($scope.currentProfile.columns, function (col) {
            return _.find(columns, {id: col.id});
          });
          var profileDerivedColumns = _.filter($scope.currentProfile.derived_columns, function (col) {
            return _.find(derived_columns, {id: col.id});
          });
          $scope.data = _.map(profileColumns, function (col) {
            var c = _.remove(deselected_columns, {id: col.id})[0];
            c.visible = true;
            return c;
          }).concat(_.map(deselected_columns, function (col) {
            col.visible = false;
            return col;
          })).concat(_.map(profileDerivedColumns, function (col) {
            var c = _.remove(deselected_derived_columns, {id: col.id})[0];
            c.visible = true;
            c.is_derived_column = true;
            c.displayName = c.name;
            return c;
          })).concat(_.map(deselected_derived_columns, function (col) {
            col.visible = false;
            col.is_derived_column = true;
            col.displayName = col.name;
            return col;
          }));

          $scope.data = inventory_service.reorderSettings($scope.data);
        } else {
          // No profiles exist
          $scope.data = _.map(deselected_columns, function (col) {
            col.visible = !col.is_extra_data;
            return col;
          });
          $scope.data = inventory_service.reorderSettings($scope.data);
        }
        initializeRowSelections();
      };
      setColumnsForCurrentProfile();

      var ignoreNextChange = true;
      $scope.$watch('currentProfile', function (newProfile, oldProfile) {
        if (ignoreNextChange) {
          ignoreNextChange = false;
          return;
        }

        if (!modified_service.isModified()) {
          switchProfile(newProfile);
        } else {
          $uibModal.open({
            template: '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch profiles without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch Profiles</button></div>'
          }).result.then(function () {
            modified_service.resetModified();
            switchProfile(newProfile);
          }).catch(function () {
            ignoreNextChange = true;
            $scope.currentProfile = oldProfile;
          });
        }
      });

      function switchProfile (newProfile) {
        ignoreNextChange = true;
        if (newProfile) {
          $scope.currentProfile = _.find($scope.profiles, {id: newProfile.id});
          inventory_service.save_last_detail_profile(newProfile.id, $scope.inventory_type);
        } else {
          $scope.currentProfile = undefined;
        }

        setColumnsForCurrentProfile();
      }

      // set up i18n
      //
      // let angular-translate be in charge ... need
      // to feed the language-only part of its $translate setting into
      // ui-grid's i18nService
      var stripRegion = function (languageTag) {
        return _.first(languageTag.split('_'));
      };
      i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

      var rowSelectionChanged = function () {
        _.forEach($scope.gridApi.grid.rows, function (row) {
          row.entity.visible = row.isSelected;
        });
        $scope.data = inventory_service.reorderSettings($scope.data);
        modified_service.setModified();
      };

      $scope.updateHeight = function () {
        var height = 0;
        _.forEach(['.header', '.page_header_container', '.section_nav_container', '.section_header_container', '.section_content.with_padding'], function (selector) {
          var element = angular.element(selector)[0];
          if (element) height += element.offsetHeight;
        });
        angular.element('#grid-container').css('height', 'calc(100vh - ' + (height + 2) + 'px)');
        angular.element('#grid-container > div').css('height', 'calc(100vh - ' + (height + 4) + 'px)');
        $scope.gridApi.core.handleWindowResize();
      };

      var currentColumns = function () {
        const columns = [];
        const derived_columns = [];
        _.forEach($scope.gridApi.grid.rows, function (row) {
          if (row.isSelected) {
            if (row.entity.is_derived_column) {
              derived_columns.push({
                id: row.entity.id
              });
            } else {
              columns.push({
                column_name: row.entity.column_name,
                id: row.entity.id,
                order: columns.length + 1,
                pinned: false,
                table_name: row.entity.table_name
              });
            }
          }
        });
        return { columns, derived_columns };
      };

      $scope.saveProfile = function () {
        var id = $scope.currentProfile.id;
        var profile = _.omit($scope.currentProfile, 'id');
        const { columns, derived_columns } = currentColumns();
        profile.columns = columns;
        profile.derived_columns = derived_columns;
        inventory_service.update_column_list_profile(id, profile).then(function (updatedProfile) {
          var index = _.findIndex($scope.profiles, {id: updatedProfile.id});
          $scope.profiles[index] = updatedProfile;
          modified_service.resetModified();
          Notification.primary('Saved ' + $scope.currentProfile.name);
        });
      };

      $scope.renameProfile = function () {
        var oldProfile = angular.copy($scope.currentProfile);

        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/settings_profile_modal.html',
          controller: 'settings_profile_modal_controller',
          resolve: {
            action: _.constant('rename'),
            data: _.constant($scope.currentProfile),
            profile_location: _.constant('Detail View Profile'),
            inventory_type: function () {
              return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            }
          }
        });

        modalInstance.result.then(function (newName) {
          $scope.currentProfile.name = newName;
          _.find($scope.profiles, {id: $scope.currentProfile.id}).name = newName;
          Notification.primary('Renamed ' + oldProfile.name + ' to ' + newName);
        });
      };

      $scope.removeProfile = function () {
        var oldProfile = angular.copy($scope.currentProfile);

        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/settings_profile_modal.html',
          controller: 'settings_profile_modal_controller',
          resolve: {
            action: _.constant('remove'),
            data: _.constant($scope.currentProfile),
            profile_location: _.constant('Detail View Profile'),
            inventory_type: function () {
              return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            }
          }
        });

        modalInstance.result.then(function () {
          _.remove($scope.profiles, oldProfile);
          modified_service.resetModified();
          $scope.currentProfile = _.first($scope.profiles);
          Notification.primary('Removed ' + oldProfile.name);
        });
      };

      $scope.newProfile = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/settings_profile_modal.html',
          controller: 'settings_profile_modal_controller',
          resolve: {
            action: _.constant('new'),
            data: currentColumns,
            profile_location: _.constant('Detail View Profile'),
            inventory_type: function () {
              return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
            }
          }
        });

        modalInstance.result.then(function (newProfile) {
          $scope.profiles.push(newProfile);
          modified_service.resetModified();
          $scope.currentProfile = _.last($scope.profiles);
          Notification.primary('Created ' + newProfile.name);
        });
      };

      $scope.isModified = function () {
        return modified_service.isModified();
      };

      $scope.gridOptions = {
        data: 'data',
        enableColumnMenus: false,
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: false,
        flatEntityAccess: true,
        gridMenuShowHideColumns: false,
        minRowsToShow: 30,
        rowTemplate: '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
        columnDefs: [{
          name: 'displayName',
          displayName: 'Column Name',
          headerCellFilter: 'translate',
          cellFilter: 'translate',
          cellTemplate: '<div class="ui-grid-cell-contents inventory-settings-cell" title="TOOLTIP" data-after-content="{$ row.entity.column_name $}"><i ng-if="row.entity.is_derived_column" class="fa fa-link" style="margin-right: 10px;"></i>{$ COL_FIELD CUSTOM_FILTERS $}</div>',
          enableHiding: false
        }],
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;
          initializeRowSelections();

          gridApi.selection.on.rowSelectionChanged($scope, rowSelectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, rowSelectionChanged);
          gridApi.draggableRows.on.rowDropped($scope, modified_service.setModified);

          _.delay($scope.updateHeight, 150);
          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });
        }
      };
    }]);
