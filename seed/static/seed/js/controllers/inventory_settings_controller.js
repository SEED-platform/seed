/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_settings', [])
  .controller('inventory_settings_controller', [
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
    'shared_fields_payload',
    'flippers',
    '$translate',
    'i18nService', // from ui-grid
    function ($scope, $window, $uibModalInstance, $stateParams, $uibModal, Notification, inventory_service, modified_service, user_service, urls, all_columns, profiles, shared_fields_payload, flippers, $translate, i18nService) {

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory = {
        id: $stateParams.inventory_id
      };
      $scope.cycle = {
        id: $stateParams.cycle_id
      };

      $scope.profiles = profiles;
      var validProfileIds = _.map(profiles, 'id');
      var lastProfileId = inventory_service.get_last_profile();
      if (_.includes(validProfileIds, lastProfileId)) {
        $scope.currentProfile = _.find($scope.profiles, {id: lastProfileId});
      } else {
        $scope.currentProfile = _.first($scope.profiles);
      }

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

      function switchProfile(newProfile) {
        $scope.currentProfile = newProfile;
        if (newProfile) {
          inventory_service.save_last_profile(newProfile.id);
        }

        // TODO refresh columns
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

      var localStorageKey = 'grid.' + $scope.inventory_type;

      $scope.showSharedBuildings = shared_fields_payload.show_shared_buildings;

      var restoreDefaults = function () {
        inventory_service.removeSettings(localStorageKey);
        $scope.data = inventory_service.loadSettings(localStorageKey, all_columns);
        _.defer(function () {
          // Set row selection
          $scope.gridApi.selection.clearSelectedRows();
          _.forEach($scope.gridApi.grid.rows, function (row) {
            if (row.entity.visible === false) row.setSelected(false);
            else row.setSelected(true);
          });
        });
      };

      var saveSettings = function () {
        $scope.data = inventory_service.reorderSettings($scope.data);
        inventory_service.saveSettings(localStorageKey, $scope.data);

        modified_service.setModified();
      };

      var rowSelectionChanged = function () {
        _.forEach($scope.gridApi.grid.rows, function (row) {
          row.entity.visible = row.isSelected;
          if (!row.isSelected && row.entity.pinnedLeft) row.entity.pinnedLeft = false;
        });
        saveSettings();
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

      $scope.saveShowSharedBuildings = function () {
        user_service.set_default_columns([], $scope.showSharedBuildings);
      };

      $scope.saveProfile = function () {
        var id = $scope.currentProfile.id;
        // TODO process column data
        var profile = _.omit($scope.currentProfile, 'id');
        inventory_service.update_settings_profile(id, profile).then(function () {
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
            data: _.constant($scope.currentProfile)
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
            data: _.constant($scope.currentProfile)
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
        // TODO process and pass current column configuration
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/settings_profile_modal.html',
          controller: 'settings_profile_modal_controller',
          resolve: {
            action: _.constant('new'),
            data: _.constant()
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

      $scope.togglePinned = function (row) {
        row.entity.pinnedLeft = !row.entity.pinnedLeft;
        if (row.entity.pinnedLeft) {
          row.entity.visible = true;
          row.setSelected(true);
        }
        saveSettings();
      };

      $scope.data = inventory_service.loadSettings(localStorageKey, all_columns);

      $scope.gridOptions = {
        data: 'data',
        enableColumnMenus: false,
        enableFiltering: true,
        enableGridMenu: true,
        enableSorting: false,
        flatEntityAccess: true,
        gridMenuCustomItems: [{
          title: $translate.instant('Reset Defaults'),
          action: restoreDefaults
        }],
        gridMenuShowHideColumns: false,
        minRowsToShow: 30,
        rowTemplate: '<div grid="grid" class="ui-grid-draggable-row" draggable="true"><div ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name" class="ui-grid-cell" ng-class="{ \'ui-grid-row-header-cell\': col.isRowHeader, \'custom\': true }" ui-grid-cell></div></div>',
        columnDefs: [{
          name: 'pinnedLeft',
          displayName: '',
          cellTemplate: '<div class="ui-grid-row-header-link">' +
          '  <a class="ui-grid-cell-contents pinnable" style="text-align: center;" ng-disabled="!COL_FIELD" ng-click="grid.appScope.togglePinned(row)">' +
          '    <i class="fa fa-thumb-tack"></i>' +
          '  </a>' +
          '</div>',
          enableColumnMenu: false,
          enableFiltering: false,
          enableSorting: false,
          width: 30
        }, {
          name: 'displayName',
          displayName: 'Column Name',
          headerCellFilter: 'translate',
          cellFilter: 'translate',
          cellTemplate: '<div class="ui-grid-cell-contents inventory-settings-cell" title="TOOLTIP" data-after-content="{$ row.entity.name $}">{$ COL_FIELD CUSTOM_FILTERS $} <span ng-if="row.entity.related" class="badge" style="margin-left: 10px;">{$ grid.appScope.inventory_type === "properties" ? ("tax lot" | translate) : ("property" | translate) $}</span></div>',
          enableHiding: false
        }],
        onRegisterApi: function (gridApi) {
          $scope.gridApi = gridApi;
          _.defer(function () {
            // Set row selection
            _.forEach($scope.gridApi.grid.rows, function (row) {
              if (row.entity.visible === false) row.setSelected(false);
              else row.setSelected(true);
            });
          });

          gridApi.selection.on.rowSelectionChanged($scope, rowSelectionChanged);
          gridApi.selection.on.rowSelectionChangedBatch($scope, rowSelectionChanged);
          gridApi.draggableRows.on.rowDropped($scope, saveSettings);

          _.delay($scope.updateHeight, 150);
          var debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
          angular.element($window).on('resize', debouncedHeightUpdate);
          $scope.$on('$destroy', function () {
            angular.element($window).off('resize', debouncedHeightUpdate);
          });
        }
      };
    }]);
