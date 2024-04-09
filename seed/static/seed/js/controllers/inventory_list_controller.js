/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_list', []).controller('inventory_list_controller', [
  '$scope',
  '$filter',
  '$window',
  '$uibModal',
  '$sce',
  '$state',
  '$stateParams',
  '$q',
  '$timeout',
  'inventory_service',
  'label_service',
  'data_quality_service',
  'geocode_service',
  'user_service',
  'derived_columns_service',
  'Notification',
  'cycles',
  'profiles',
  'current_profile',
  'filter_groups',
  'current_filter_group',
  'filter_groups_service',
  'all_columns',
  'derived_columns_payload',
  'urls',
  'spinner_utility',
  'naturalSort',
  '$translate',
  'uiGridConstants',
  'i18nService',
  'organization_payload',
  'gridUtil',
  'uiGridGridMenuService',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $filter,
    $window,
    $uibModal,
    $sce,
    $state,
    $stateParams,
    $q,
    $timeout,
    inventory_service,
    label_service,
    data_quality_service,
    geocode_service,
    user_service,
    derived_columns_service,
    Notification,
    cycles,
    profiles,
    current_profile,
    filter_groups,
    current_filter_group,
    filter_groups_service,
    all_columns,
    derived_columns_payload,
    urls,
    spinner_utility,
    naturalSort,
    $translate,
    uiGridConstants,
    i18nService,
    organization_payload,
    gridUtil,
    uiGridGridMenuService
  ) {
    spinner_utility.show();
    $scope.selectedCount = 0;
    $scope.selectedParentCount = 0;
    $scope.selectedOrder = [];
    $scope.columnDisplayByName = {};
    for (const col of all_columns) {
      $scope.columnDisplayByName[col.name] = col.displayName;
    }

    $scope.inventory_type = $stateParams.inventory_type;
    $scope.data = [];
    const lastCycleId = inventory_service.get_last_cycle();
    $scope.cycle = {
      selected_cycle: _.find(cycles.cycles, { id: lastCycleId }) || _.first(cycles.cycles),
      cycles: cycles.cycles
    };
    $scope.organization = organization_payload.organization;

    // set up i18n
    //
    // let angular-translate be in charge ... need
    // to feed the language-only part of its $translate setting into
    // ui-grid's i18nService
    const stripRegion = (languageTag) => _.first(languageTag.split('_'));
    i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

    // Column List Profile
    $scope.profiles = profiles;
    $scope.currentProfile = current_profile;

    if ($scope.currentProfile) {
      $scope.columns = [];
      // add columns
      _.forEach($scope.currentProfile.columns, (col) => {
        const foundCol = _.find(all_columns, { id: col.id });
        if (foundCol) {
          foundCol.pinnedLeft = col.pinned;
          $scope.columns.push(foundCol);
        }
      });
    } else {
      // No profiles exist
      $scope.columns = _.reject(all_columns, 'is_extra_data');
    }

    // Filter Groups
    $scope.filterGroups = [
      {
        id: -1,
        name: '-- No filter --',
        inventory_type: $scope.inventory_type,
        and_labels: [],
        or_labels: [],
        exclude_labels: [],
        query_dict: {}
      }
    ];
    $scope.filterGroups = $scope.filterGroups.concat(filter_groups);
    if (current_filter_group === null) {
      $scope.currentFilterGroup = $scope.filterGroups[0];
    } else {
      $scope.currentFilterGroup = current_filter_group;
    }
    $scope.currentFilterGroupId = current_filter_group ? String(current_filter_group.id) : '-1';

    $scope.Modified = false;

    $scope.new_filter_group = () => {
      const and_label_ids = $scope.selected_and_labels.map((l) => l.id);
      const or_label_ids = $scope.selected_or_labels.map((l) => l.id);
      const exclude_label_ids = $scope.selected_exclude_labels.map((l) => l.id);
      const filter_group_inventory_type = $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
      const query_dict = inventory_service.get_format_column_filters($scope.column_filters);

      const filterGroupData = {
        query_dict,
        inventory_type: filter_group_inventory_type,
        and_labels: and_label_ids,
        or_labels: or_label_ids,
        exclude_labels: exclude_label_ids
      };

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/filter_group_modal.html`,
        controller: 'filter_group_modal_controller',
        resolve: {
          action: () => 'new',
          data: () => filterGroupData
        }
      });

      modalInstance.result.then((new_filter_group) => {
        $scope.filterGroups.push(new_filter_group);
        $scope.Modified = false;
        $scope.currentFilterGroup = _.last($scope.filterGroups);
        $scope.currentFilterGroupId = String(new_filter_group.id);
        updateCurrentFilterGroup($scope.currentFilterGroup);

        Notification.primary(`Created ${$scope.currentFilterGroup.name}`);
      });
    };

    $scope.remove_filter_group = () => {
      const oldFilterGroupName = $scope.currentFilterGroup.name;

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/filter_group_modal.html`,
        controller: 'filter_group_modal_controller',
        resolve: {
          action: () => 'remove',
          data: () => $scope.currentFilterGroup
        }
      });

      modalInstance.result.then(() => {
        _.remove($scope.filterGroups, $scope.currentFilterGroup);
        $scope.Modified = false;
        $scope.currentFilterGroup = _.first($scope.filterGroups);
        $scope.currentFilterGroupId = String($scope.currentFilterGroup.id);
        updateCurrentFilterGroup($scope.currentFilterGroup);

        Notification.primary(`Removed ${oldFilterGroupName}`);
      });
    };

    $scope.rename_filter_group = () => {
      const oldFilterGroup = angular.copy($scope.currentFilterGroup);

      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/filter_group_modal.html`,
        controller: 'filter_group_modal_controller',
        resolve: {
          action: () => 'rename',
          data: () => $scope.currentFilterGroup
        }
      });

      modalInstance.result.then((newName) => {
        $scope.currentFilterGroup.name = newName;
        _.find($scope.filterGroups, { id: $scope.currentFilterGroup.id }).name = newName;
        Notification.primary(`Renamed ${oldFilterGroup.name} to ${newName}`);
      });
    };

    $scope.save_filter_group = () => {
      const and_label_ids = [];
      const or_label_ids = [];
      const exclude_label_ids = [];
      for (const label of $scope.selected_and_labels) {
        and_label_ids.push(label.id);
      }
      for (const label of $scope.selected_or_labels) {
        or_label_ids.push(label.id);
      }
      for (const label of $scope.selected_exclude_labels) {
        exclude_label_ids.push(label.id);
      }
      const filter_group_inventory_type = $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
      const query_dict = inventory_service.get_format_column_filters($scope.column_filters);
      const filterGroupData = {
        name: $scope.currentFilterGroup.name,
        query_dict,
        inventory_type: filter_group_inventory_type,
        and_labels: and_label_ids,
        or_labels: or_label_ids,
        exclude_labels: exclude_label_ids
      };
      filter_groups_service.update_filter_group($scope.currentFilterGroup.id, filterGroupData).then((result) => {
        $scope.currentFilterGroup = result;
        const currentFilterGroupIndex = $scope.filterGroups.findIndex((fg) => fg.id === result.id);
        $scope.filterGroups[currentFilterGroupIndex] = result;
        $scope.Modified = false;
        Notification.primary(`Saved ${$scope.currentFilterGroup.name}`);
      });
    };

    // compare filters if different then true, then compare labels. All must be the same to return false
    $scope.isModified = () => {
      if ($scope.currentFilterGroup == null) return false;

      if ($scope.filterGroups.length > 0) {
        const current_filters = inventory_service.get_format_column_filters($scope.column_filters);
        const saved_filters = $scope.currentFilterGroup.query_dict;
        const current_and_labels = new Set($scope.selected_and_labels.map((l) => l.id));
        const current_or_labels = new Set($scope.selected_or_labels.map((l) => l.id));
        const current_exclude_labels = new Set($scope.selected_exclude_labels.map((l) => l.id));

        const saved_and_labels = new Set($scope.currentFilterGroup.and_labels);
        const saved_or_labels = new Set($scope.currentFilterGroup.or_labels);
        const saved_exclude_labels = new Set($scope.currentFilterGroup.exclude_labels);

        $scope.Modified = !(
          _.isEqual(current_filters, saved_filters) &&
           _.isEqual(current_and_labels, saved_and_labels) &&
           _.isEqual(current_or_labels, saved_or_labels) &&
           _.isEqual(current_exclude_labels, saved_exclude_labels)
        );
      }
      return $scope.Modified;
    };

    const getTableFilter = (value, operator) => {
      switch (operator) {
        case 'exact':
          return `"${value}"`;
        case 'icontains':
          return value;
        case 'gt':
          return `>${value}`;
        case 'gte':
          return `>=${value}`;
        case 'lt':
          return `<${value}`;
        case 'lte':
          return `<=${value}`;
        case 'ne':
          return `!="${value}"`;
        default:
          console.error('Unknown action:', elSelectActions.value, 'Update "run_action()"');
      }
    };

    const updateCurrentFilterGroup = (filterGroup) => {
      // Set current filter group
      $scope.currentFilterGroup = filterGroup;

      if (filterGroup) {
        filter_groups_service.save_last_filter_group($scope.currentFilterGroup.id, $scope.inventory_type);

        // Update labels
        $scope.isModified();
        $scope.selected_and_labels = _.filter($scope.labels, (label) => _.includes($scope.currentFilterGroup.and_labels, label.id));
        $scope.selected_or_labels = _.filter($scope.labels, (label) => _.includes($scope.currentFilterGroup.or_labels, label.id));
        $scope.selected_exclude_labels = _.filter($scope.labels, (label) => _.includes($scope.currentFilterGroup.exclude_labels, label.id));
        $scope.filterUsingLabels();

        // clear table filters
        $scope.gridApi.grid.columns.forEach((column) => {
          column.filters[0] = {
            term: null
          };
        });

        // write new filter in table
        for (const key in $scope.currentFilterGroup.query_dict) {
          const value = $scope.currentFilterGroup.query_dict[key];
          const [column_name, operator] = key.split('__');

          // TODO: if this column is hidden, this whole operation falls apart.
          const column = $scope.gridApi.grid.columns.find(({ colDef }) => colDef.name === column_name);

          if (column.filters[0].term == null) {
            column.filters[0].term = getTableFilter(value, operator);
          } else {
            column.filters[0].term += `, ${getTableFilter(value, operator)}`;
          }
        }

        // update filtering
        updateColumnFilterSort();
      }
    };

    $scope.check_for_filter_group_changes = (currentFilterGroupId, oldFilterGroupId) => {
      currentFilterGroupId = +currentFilterGroupId;

      const selectedFilterGroup = $scope.filterGroups.find(({ id }) => id === currentFilterGroupId);

      if ($scope.Modified) {
        $uibModal
          .open({
            template:
              '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch filter groups without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch Filter Groups</button></div>',
            backdrop: 'static'
          })
          .result.then(() => {
            $scope.Modified = false;
            updateCurrentFilterGroup(selectedFilterGroup);
          })
          .catch(() => {
            $scope.currentFilterGroupId = String(oldFilterGroupId);
          });
      } else {
        updateCurrentFilterGroup(selectedFilterGroup);
      }
    };

    // restore_response is a state tracker for avoiding multiple reloads
    // of the inventory data when initializing the page.
    // The problem occurs due to retriggering of data reload, summarized by this issue:
    // https://github.com/angular-ui/ui-grid/issues/5280
    // Note that this implementation can _still_ result in an unwanted race condition
    // but for the most part seems to avoid it without arbitrary wait timers
    const RESTORE_NOT_STARTED = 'not started';
    const RESTORE_SETTINGS = 'restoring settings';
    const RESTORE_SETTINGS_DONE = 'restore settings done';
    const RESTORE_COMPLETE = 'restore done';
    $scope.restore_status = RESTORE_NOT_STARTED;
    $scope.$watch('restore_status', () => {
      // Load the initial data for the page
      // this only happens ONCE (after the ui-grid's saveState.restore has completed)
      if ($scope.restore_status === RESTORE_SETTINGS_DONE) {
        updateColumnFilterSort();
        get_labels();
        $scope.restore_status = RESTORE_COMPLETE;
      }
    });

    // stores columns that have filtering and/or sorting applied
    $scope.column_filters = [];
    $scope.column_sorts = [];

    // remove editing on list inputs (ngTagsInput doesn't support readonly yet)
    const findList = {};
    for (const elementId of ['filters-list', 'sort-list']) {
      findList[elementId] = { attempts: 0 };
      const element = document.getElementById(elementId);
      if (!element) continue;
      findList[elementId].interval = setInterval(() => {
        const listInput = element.getElementsByTagName('input')[0];
        if (listInput) {
          listInput.readOnly = true;
          clearInterval(findList[elementId].interval);
        }
        findList[elementId].attempts++;
        if (findList[elementId].attempts > 10) {
          clearInterval(findList[elementId].interval);
        }
      }, 1000);
    }

    // Find labels that should be displayed and organize by applied inventory id
    $scope.show_labels_by_inventory_id = {};
    $scope.build_labels = () => {
      $scope.show_labels_by_inventory_id = {};
      for (const n in $scope.labels) {
        const label = $scope.labels[n];
        if (label.show_in_list) {
          for (const m in label.is_applied) {
            const id = label.is_applied[m];
            if (!$scope.show_labels_by_inventory_id[id]) {
              $scope.show_labels_by_inventory_id[id] = [];
            }
            $scope.show_labels_by_inventory_id[id].push(label);
          }
        }
      }
    };

    // Builds the html to display labels associated with this row entity
    $scope.display_labels = (entity) => {
      const id = $scope.inventory_type === 'properties' ? entity.property_view_id : entity.taxlot_view_id;
      const labels = [];
      const titles = [];
      if ($scope.show_labels_by_inventory_id[id]) {
        for (const i in $scope.show_labels_by_inventory_id[id]) {
          const label = $scope.show_labels_by_inventory_id[id][i];
          labels.push('<span class="', $scope.show_full_labels ? 'label' : 'label-bar', ' label-', label.label, '">', $scope.show_full_labels ? label.text : '', '</span>');
          titles.push(label.text);
        }
      }
      return ['<span title="', titles.join(', '), '" class="label-bars" style="overflow-x:scroll">', labels.join(''), '</span>'].join('');
    };

    $scope.show_full_labels = false;
    $scope.toggle_labels = () => {
      $scope.show_full_labels = !$scope.show_full_labels;
      setTimeout(() => {
        $scope.gridApi.grid.getColumn('labels').width = $scope.get_label_column_width();
        const icon = document.getElementById('label-header-icon');
        icon.classList.add($scope.show_full_labels ? 'fa-chevron-circle-left' : 'fa-chevron-circle-right');
        icon.classList.remove($scope.show_full_labels ? 'fa-chevron-circle-right' : 'fa-chevron-circle-left');
        $scope.gridApi.grid.refresh();
      }, 0);
    };

    $scope.max_label_width = 750;
    $scope.get_label_column_width = () => {
      if (!$scope.show_full_labels) {
        return 31;
      }
      let maxWidth = 0;
      const renderContainer = document.body.getElementsByClassName('ui-grid-render-container-left')[0];
      const col = $scope.gridApi.grid.getColumn('labels');
      const cells = renderContainer.querySelectorAll(`.${uiGridConstants.COL_CLASS_PREFIX}${col.uid} .ui-grid-cell-contents`);
      Array.prototype.forEach.call(cells, (cell) => {
        gridUtil.fakeElement(cell, {}, (newElm) => {
          const e = angular.element(newElm);
          e.attr('style', 'float: left;');
          const width = gridUtil.elementWidth(e);
          if (width > maxWidth) {
            maxWidth = width;
          }
        });
      });
      maxWidth = Math.max(31, maxWidth + 2);
      return Math.min(maxWidth, $scope.max_label_width);
    };

    $scope.show_tags_input = { and: true, or: true, exclude: true };
    // Reduce labels to only records found in the current cycle
    $scope.selected_and_labels = [];
    $scope.selected_or_labels = [];
    $scope.selected_exclude_labels = [];

    const localStorageKey = `grid.${$scope.inventory_type}`;
    const localStorageLabelKey = `grid.${$scope.inventory_type}.labels`;

    // reset the selected_labels to [] and re-render the <tags-input> component as invalid text is not attached to the model.
    $scope.clear_labels = (action) => {
      const selected_labels = {
        and: $scope.selected_and_labels,
        or: $scope.selected_or_labels,
        exclude: $scope.selected_exclude_labels
      };
      selected_labels[action].splice(0);
      $scope.show_tags_input[action] = false;
      // immediately re-render
      setTimeout(() => {
        $scope.$apply(() => {
          $scope.show_tags_input[action] = true;
        });
      }, 0);
      $scope.filterUsingLabels();
    };

    let ignoreNextChange = true;
    $scope.$watch('currentProfile', (newProfile) => {
      if (ignoreNextChange) {
        ignoreNextChange = false;
        return;
      }

      inventory_service.save_last_profile(newProfile.id, $scope.inventory_type);
      spinner_utility.show();
      $window.location.reload();
    });

    $scope.newProfile = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/settings_profile_modal.html`,
        controller: 'settings_profile_modal_controller',
        resolve: {
          action: () => 'new',
          data: () => ({
            columns: currentColumns(),
            derived_columns: []
          }),
          profile_location: () => 'List View Profile',
          inventory_type: () => ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')
        }
      });

      return modalInstance.result.then((newProfile) => {
        $scope.profiles.push(newProfile);
        ignoreNextChange = true;
        $scope.currentProfile = _.last($scope.profiles);
        inventory_service.save_last_profile(newProfile.id, $scope.inventory_type);
      });
    };

    $scope.open_show_populated_columns_modal = () => {
      if (!profiles.length) {
        // Create a profile first
        $scope.newProfile().then(() => {
          populated_columns_modal();
        });
      } else {
        populated_columns_modal();
      }
    };

    function populated_columns_modal() {
      $uibModal.open({
        backdrop: 'static',
        templateUrl: `${urls.static_url}seed/partials/show_populated_columns_modal.html`,
        controller: 'show_populated_columns_modal_controller',
        resolve: {
          columns: () => all_columns,
          currentProfile: () => $scope.currentProfile,
          cycle: () => $scope.cycle.selected_cycle,
          inventory_type: () => $stateParams.inventory_type,
          provided_inventory: () => null
        }
      });
    }

    $scope.show_access_level_instances = true;
    $scope.toggle_access_level_instances = () => {
      $scope.show_access_level_instances = !$scope.show_access_level_instances;
      $scope.gridOptions.columnDefs.forEach((col) => {
        if (col.group === 'access_level_instance') {
          col.visible = $scope.show_access_level_instances;
        }
      });
      $scope.gridApi.core.refresh();
    };

    $scope.loadLabelsForFilter = (
      query // Find all labels associated with the current cycle.
    ) => _.filter($scope.labels, (lbl) => {
      if (_.isEmpty(query)) {
        // Empty query so return the whole list.
        return true;
      }
      // Only include element if its name contains the query string.
      return _.includes(_.toLower(lbl.name), _.toLower(query));
    });

    $scope.filterUsingLabels = () => {
      inventory_service.saveSelectedLabels(localStorageLabelKey, _.map($scope.selected_and_labels, 'id'), 'and');
      inventory_service.saveSelectedLabels(localStorageLabelKey, _.map($scope.selected_or_labels, 'id'), 'or');
      inventory_service.saveSelectedLabels(localStorageLabelKey, _.map($scope.selected_exclude_labels, 'id'), 'exclude');
      $scope.load_inventory(1);
      $scope.isModified();
    };

    /**
     Opens the update building labels modal.
     All further actions for labels happen with that modal and its related controller,
     including creating a new label or applying to/removing from a building.
     When the modal is closed, and refresh labels.
     */
    $scope.open_update_labels_modal = (selectedViewIds) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/update_item_labels_modal.html`,
        controller: 'update_item_labels_modal_controller',
        resolve: {
          inventory_ids: () => selectedViewIds,
          inventory_type: () => $scope.inventory_type,
          is_ali_root: () => $scope.menu.user.is_ali_root
        }
      });
      modalInstance.result.then(() => {
        // dialog was closed with 'Done' button.
        get_labels();
        $scope.load_inventory(1);
      });
    };

    /**
     Opens the postoffice modal for sending emails.
     'property_state_id's/'taxlot_state_id's for selected rows are stored as part of the resolver
     */
    $scope.open_postoffice_modal = (selectedViewIds) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/postoffice_modal.html`,
        controller: 'postoffice_modal_controller',
        resolve: {
          property_states: () => ($scope.inventory_type === 'properties' ? selectedViewIds : []),
          taxlot_states: () => ($scope.inventory_type === 'taxlots' ? selectedViewIds : []),
          inventory_type: () => $scope.inventory_type
        }
      });
    };

    $scope.open_merge_modal = (selectedViewIds) => {
      spinner_utility.show();
      selectedViewIds.reverse();
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/merge_modal.html`,
        controller: 'merge_modal_controller',
        windowClass: 'merge-modal',
        resolve: {
          columns() {
            let func;
            if ($stateParams.inventory_type === 'properties') func = inventory_service.get_mappable_property_columns;
            else func = inventory_service.get_mappable_taxlot_columns;

            return func().then((columns) => _.map(columns, (column) => _.pick(column, ['column_name', 'displayName', 'id', 'is_extra_data', 'name', 'table_name', 'merge_protection'])));
          },
          data() {
            const viewIdProp = $scope.inventory_type === 'properties' ? 'property_view_id' : 'taxlot_view_id';
            const data = new Array(selectedViewIds.length);

            if ($scope.inventory_type === 'properties') {
              return inventory_service.get_properties(1, undefined, $scope.cycle.selected_cycle, -1, selectedViewIds).then((inventory_data) => {
                _.forEach(selectedViewIds, (id, index) => {
                  const match = _.find(inventory_data.results, [viewIdProp, id]);
                  if (match) {
                    data[index] = match;
                  }
                });
                return data;
              });
            }
            if ($scope.inventory_type === 'taxlots') {
              return inventory_service.get_taxlots(1, undefined, $scope.cycle.selected_cycle, -1, selectedViewIds).then((inventory_data) => {
                _.forEach(selectedViewIds, (id, index) => {
                  const match = _.find(inventory_data.results, [viewIdProp, id]);
                  if (match) {
                    data[index] = match;
                  }
                });
                return data;
              });
            }
          },
          inventory_type: () => $scope.inventory_type,
          has_meters() {
            if ($scope.inventory_type === 'properties') {
              return inventory_service.properties_meters_exist(selectedViewIds).then((has_meters) => has_meters);
            }
            return false;
          },
          org_id: () => $scope.organization.id
        }
      });
      modalInstance.result.then(() => {
        // dialog was closed with 'Merge' button.
        $scope.selectedOrder = [];
        $scope.load_inventory(1);
      });
    };

    const propertyPolygonCache = {};
    const taxlotPolygonCache = {};
    const propertyFootprintColumn = _.find($scope.columns, { column_name: 'property_footprint', table_name: 'PropertyState' });
    const taxlotFootprintColumn = _.find($scope.columns, { column_name: 'taxlot_footprint', table_name: 'TaxLotState' });
    $scope.polygon = (record, tableName) => {
      const outputSize = 180;

      let cache;
      let field;
      if (tableName === 'PropertyState') {
        cache = propertyPolygonCache;
        field = propertyFootprintColumn.name;
      } else {
        cache = taxlotPolygonCache;
        field = taxlotFootprintColumn.name;
      }

      if (!_.has(cache, record.id)) {
        let footprint;
        try {
          footprint = Terraformer.WKT.parse(record[field]);
        } catch (e) {
          return record[field];
        }
        const coords = Terraformer.toMercator(footprint).coordinates[0];
        const envelope = Terraformer.Tools.calculateEnvelope(footprint);

        // padding to allow for svg stroke
        const padding = 2;
        const scale = (outputSize - padding) / Math.max(envelope.h, envelope.w);

        const width = envelope.w <= envelope.h ? Math.ceil(envelope.w * scale + padding) : outputSize;
        const height = envelope.h <= envelope.w ? Math.ceil(envelope.h * scale + padding) : outputSize;

        const xOffset = (width - envelope.w * scale) / 2;
        const yOffset = (height - envelope.h * scale) / 2;

        const points = _.map(coords, (coord) => {
          const x = _.round((coord[0] - envelope.x) * scale + xOffset, 2);
          const y = _.round(height - ((coord[1] - envelope.y) * scale + yOffset), 2);
          return `${x},${y}`;
        });

        const svg = `<svg height="${height}" width="${width}"><polygon points="${_.initial(points).join(' ')}" style="fill:#ffab66;stroke:#aaa;stroke-width:1;" /></svg>`;

        cache[record.id] = $sce.trustAsHtml(svg);
      }
      return cache[record.id];
    };

    $scope.run_data_quality_check = (selectedViewIds) => {
      spinner_utility.show();

      const property_view_ids = $scope.inventory_type === 'properties' ? selectedViewIds : [];
      const taxlot_view_ids = $scope.inventory_type === 'taxlots' ? selectedViewIds : [];

      data_quality_service.start_data_quality_checks(property_view_ids, taxlot_view_ids).then((response) => {
        data_quality_service
          .data_quality_checks_status(response.progress_key)
          .then((result) => {
            data_quality_service.get_data_quality_results($scope.organization.id, result.unique_id).then((dq_result) => {
              const modalInstance = $uibModal.open({
                templateUrl: `${urls.static_url}seed/partials/data_quality_modal.html`,
                controller: 'data_quality_modal_controller',
                size: 'lg',
                resolve: {
                  dataQualityResults: () => dq_result,
                  name: () => null,
                  uploaded: () => null,
                  run_id: () => result.unique_id,
                  orgId: () => $scope.organization.id
                }
              });
              modalInstance.result.then(() => {
                // dialog was closed with 'Done' button.
                get_labels();
              });
            });
          })
          .finally(() => {
            spinner_utility.hide();
          });
      });
    };

    // Column defaults. Column description popover
    const defaults = {
      headerCellFilter: 'translate',
      headerCellTemplate:
        '<div role="columnheader" ng-class="{ \'sortable\': sortable, \'ui-grid-header-cell-last-col\': isLastCol }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : (!col.sort.direction ? \'none\' : \'other\'))}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex" uib-tooltip="{{ col.colDef.column_description }}" tooltip-append-to-body="true"><span class="ui-grid-header-cell-label" ui-grid-one-bind-id-grid="col.uid + \'-header-text\'">{{ col.displayName CUSTOM_FILTERS }}</span> <span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" ui-grid-visible="col.sort.direction" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-blank\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 )  : null}}" aria-hidden="true"></i> <sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div><div role="button" tabindex="0" ui-grid-one-bind-id-grid="col.uid + \'-menu-button\'" class="ui-grid-column-menu-button" ng-if="grid.options.enableColumnMenus && !col.isRowHeader  && col.colDef.enableColumnMenu !== false" ng-click="toggleMenu($event)" ng-keydown="headerCellArrowKeyDown($event)" ui-grid-one-bind-aria-label="i18n.headerCell.aria.columnMenuButtonLabel" aria-expanded="{{col.menuShown}}" aria-haspopup="true"><i class="ui-grid-icon-angle-down" aria-hidden="true">&nbsp;</i></div><div ui-grid-filter ng-hide="col.filterContainer === \'columnMenu\'"></div></div>',
      minWidth: 75,
      width: 150
    };
    _.map($scope.columns, (col) => {
      const options = {};
      // Modify cellTemplate
      if (_.isMatch(col, { column_name: 'property_footprint', table_name: 'PropertyState' })) {
        col.cellTemplate =
          '<div class="ui-grid-cell-contents" uib-tooltip-html="grid.appScope.polygon(row.entity, \'PropertyState\')" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
      } else if (_.isMatch(col, { column_name: 'taxlot_footprint', table_name: 'TaxLotState' })) {
        col.cellTemplate =
          '<div class="ui-grid-cell-contents" uib-tooltip-html="grid.appScope.polygon(row.entity, \'TaxLotState\')" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
      } else {
        col.cellTemplate = '<div class="ui-grid-cell-contents" uib-tooltip="{{COL_FIELD CUSTOM_FILTERS}}" tooltip-append-to-body="true" tooltip-popup-delay="500">{{COL_FIELD CUSTOM_FILTERS}}</div>';
      }

      // Modify headerCellClass
      if (col.derived_column) {
        col.headerCellClass = 'derived-column-display-name';
      }

      // Modify misc
      if (col.data_type === 'datetime') {
        options.cellFilter = "date:'yyyy-MM-dd h:mm a'";
      } else if (
        ['area', 'eui', 'float', 'number'].includes(col.data_type) &&
        !['longitude', 'latitude'].includes(col.column_name) // we need the whole number for these
      ) {
        options.cellFilter = `tolerantNumber: ${$scope.organization.display_decimal_places}`;
      } else if (col.is_derived_column) {
        options.cellFilter = `number: ${$scope.organization.display_decimal_places}`;
      }

      if (col.column_name === 'number_properties' && col.related) options.treeAggregationType = 'total';
      else if (col.related || col.is_extra_data) options.treeAggregationType = 'uniqueList';
      return _.defaults(col, options, defaults);
    });

    // Add access level instances to grid
    for (const level of $scope.organization.access_level_names.reverse().slice(0, -1)) {
      $scope.columns.unshift({
        name: level,
        displayName: level,
        group: 'access_level_instance',
        enableColumnMenu: true,
        enableColumnMoving: false,
        enableColumnResizing: true,
        enableFiltering: true,
        enableHiding: true,
        enableSorting: true,
        enablePinning: false,
        exporterSuppressExport: true,
        pinnedLeft: true,
        visible: true,
        width: 100,
        cellClass: 'ali-cell',
        headerCellClass: 'ali-header'
      });
    }
    // The meters_exist_indicator column is only applicable to properties
    if ($stateParams.inventory_type === 'properties') {
      $scope.columns.unshift(
        {
          name: 'merged_indicator',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <div title="${$translate.instant('Merged Records')}" class="ui-grid-cell-contents merged-indicator">` +
            '    <i class="fa-solid fa-code-fork fa-lg fa-rotate-180" ng-class="{\'text-muted\': !row.entity.merged_indicator, \'text-info\': row.entity.merged_indicator}"></i>' +
            '  </div>' +
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
        {
          name: 'notes_count',
          displayName: '',
          headerCellTemplate:
            '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : \'none\')}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex"><span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-up-dir translucent\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 ) : null}}" aria-hidden="true"></i><sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div></div>',
          cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <a title="${$translate.instant(
              'Go to Notes'
            )}" class="ui-grid-cell-contents notes-button" ng-if="row.entity.$$treeLevel === 0" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'properties', view_id: row.entity.property_view_id, record: row.entity} : {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id, record: row.entity})">` +
            "    <i class=\"fa fa-comment\" ng-class=\"{'text-muted': !row.entity.notes_count}\"></i><div>{$ row.entity.notes_count > 999 ? '> 999' : row.entity.notes_count || '' $}</div>" +
            '  </a>' +
            `  <a title="${$translate.instant(
              'Go to Notes'
            )}" class="ui-grid-cell-contents notes-button" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id, record: row.entity} : {inventory_type: 'properties', view_id: row.entity.property_view_id, record: row.entity})">` +
            "    <i class=\"fa fa-comment\" ng-class=\"{'text-muted': !row.entity.notes_count}\"></i><div>{$ row.entity.notes_count > 999 ? '> 999' : row.entity.notes_count || '' $}</div>" +
            '  </a>' +
            '</div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: true,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: 30
        },
        {
          name: 'meters_exist_indicator',
          displayName: '',
          headerCellTemplate:
            '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : \'none\')}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex"><span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-up-dir translucent\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 ) : null}}" aria-hidden="true"></i><sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div></div>',
          cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <a title="${$translate.instant(
              'Go to Meters'
            )}" class="ui-grid-cell-contents meters-exist-indicator" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail_meters(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'properties', view_id: row.entity.property_view_id} : {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id})">` +
            '    <i class="fa fa-bolt" ng-class="{\'text-muted\': !row.entity.meters_exist_indicator, \'text-info\': row.entity.meters_exist_indicator}"></i>' +
            '  </a>' +
            '</div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: true,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: 30
        },
        {
          name: 'id',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <a title="${$translate.instant(
              'Go to Detail Page'
            )}" class="ui-grid-cell-contents" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'properties', view_id: row.entity.property_view_id} : {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id})">` +
            '    <i class="ui-grid-icon-info-circled"></i>' +
            '  </a>' +
            `  <a title="${$translate.instant(
              'Go to Detail Page'
            )}" class="ui-grid-cell-contents" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ui-sref="inventory_detail(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id} : {inventory_type: 'properties', view_id: row.entity.property_view_id})">` +
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
        {
          name: 'labels',
          displayName: '',
          headerCellTemplate: '<i ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents fas fa-chevron-circle-right" id="label-header-icon" style="margin:2px; float:right;"></i>',
          cellTemplate: '<div ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents" ng-bind-html="grid.appScope.display_labels(row.entity)"></div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: false,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: $scope.get_label_column_width(),
          maxWidth: $scope.max_label_width
        }
      );
    } else {
      $scope.columns.unshift(
        {
          name: 'merged_indicator',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <div title="${$translate.instant('Merged Records')}" class="ui-grid-cell-contents merged-indicator">` +
            '    <i class="fa-solid fa-code-fork fa-lg fa-rotate-180" ng-class="{\'text-muted\': !row.entity.merged_indicator, \'text-info\': row.entity.merged_indicator}"></i>' +
            '  </div>' +
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
        {
          name: 'notes_count',
          displayName: '',
          headerCellTemplate:
            '<div role="columnheader" ng-class="{ \'sortable\': sortable }" ui-grid-one-bind-aria-labelledby-grid="col.uid + \'-header-text \' + col.uid + \'-sortdir-text\'" aria-sort="{{col.sort.direction == asc ? \'ascending\' : ( col.sort.direction == desc ? \'descending\' : \'none\')}}"><div role="button" tabindex="0" ng-keydown="handleKeyDown($event)" class="ui-grid-cell-contents ui-grid-header-cell-primary-focus" col-index="renderIndex"><span ui-grid-one-bind-id-grid="col.uid + \'-sortdir-text\'" aria-label="{{getSortDirectionAriaLabel()}}"><i ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-up-dir translucent\': !col.sort.direction }" title="{{isSortPriorityVisible() ? i18n.headerCell.priority + \' \' + ( col.sort.priority + 1 ) : null}}" aria-hidden="true"></i><sub ui-grid-visible="isSortPriorityVisible()" class="ui-grid-sort-priority-number">{{col.sort.priority + 1}}</sub></span></div></div>',
          cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <a title="${$translate.instant(
              'Go to Notes'
            )}" class="ui-grid-cell-contents notes-button" ng-if="row.entity.$$treeLevel === 0" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'properties', view_id: row.entity.property_view_id, record: row.entity} : {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id, record: row.entity})">` +
            "    <i class=\"fa fa-comment\" ng-class=\"{'text-muted': !row.entity.notes_count}\"></i><div>{$ row.entity.notes_count > 999 ? '> 999' : row.entity.notes_count || '' $}</div>" +
            '  </a>' +
            `  <a title="${$translate.instant(
              'Go to Notes'
            )}" class="ui-grid-cell-contents notes-button" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ng-click="grid.appScope.view_notes(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id, record: row.entity} : {inventory_type: 'properties', view_id: row.entity.property_view_id, record: row.entity})">` +
            "    <i class=\"fa fa-comment\" ng-class=\"{'text-muted': !row.entity.notes_count}\"></i><div>{$ row.entity.notes_count > 999 ? '> 999' : row.entity.notes_count || '' $}</div>" +
            '  </a>' +
            '</div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: true,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: 30
        },
        {
          name: 'id',
          displayName: '',
          headerCellTemplate: '<span></span>', // remove header
          cellTemplate:
            '<div class="ui-grid-row-header-link">' +
            `  <a title="${$translate.instant(
              'Go to Detail Page'
            )}" class="ui-grid-cell-contents" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'properties', view_id: row.entity.property_view_id} : {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id})">` +
            '    <i class="ui-grid-icon-info-circled"></i>' +
            '  </a>' +
            `  <a title="${$translate.instant(
              'Go to Detail Page'
            )}" class="ui-grid-cell-contents" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ui-sref="inventory_detail(grid.appScope.inventory_type === 'properties' ? {inventory_type: 'taxlots', view_id: row.entity.taxlot_view_id} : {inventory_type: 'properties', view_id: row.entity.property_view_id})">` +
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
        {
          name: 'labels',
          displayName: '',
          headerCellTemplate: '<i ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents fas fa-chevron-circle-right" id="label-header-icon" style="margin:2px; float:right;"></i>',
          cellTemplate: '<div ng-click="grid.appScope.toggle_labels()" class="ui-grid-cell-contents" ng-bind-html="grid.appScope.display_labels(row.entity)"></div>',
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: false,
          exporterSuppressExport: true,
          pinnedLeft: true,
          visible: true,
          width: $scope.get_label_column_width(),
          maxWidth: $scope.max_label_width
        }
      );
    }

    // disable sorting (but not filtering) on related data until the backend can filter/sort over two models
    for (const i in $scope.columns) {
      const column = $scope.columns[i];
      if (column.related) {
        column.enableSorting = false;
        // let title = 'Filtering disabled for property columns on the taxlot list.';
        // if ($scope.inventory_type === 'properties') {
        //   title = 'Filtering disabled for taxlot columns on the property list.';
        // }
      }
      if (column.derived_column != null) {
        column.enableSorting = false;
        const title = 'Sorting and filtering disabled for derived columns.';
        column.filterHeaderTemplate = `<div class="ui-grid-filter-container"><input type="text" title="${title}" class="ui-grid-filter-input" disabled=disabled />`;
      }
    }

    const findColumn = _.memoize((name) => _.find(all_columns, { name }));

    // Data
    const processData = (data) => {
      if (_.isUndefined(data)) data = $scope.data;
      const visibleColumns = [
        ..._.map($scope.columns, 'name'),
        ...['$$treeLevel', 'notes_count', 'meters_exist_indicator', 'merged_indicator', 'id', 'property_state_id', 'property_view_id', 'taxlot_state_id', 'taxlot_view_id'],
        ...$scope.organization.access_level_names
      ];

      const columnsToAggregate = _.filter($scope.columns, 'treeAggregationType').reduce((obj, col) => {
        obj[col.name] = col.treeAggregationType;
        return obj;
      }, {});
      const columnNamesToAggregate = _.keys(columnsToAggregate);

      const roots = data.length;
      for (let i = 0, trueIndex = 0; i < roots; ++i, ++trueIndex) {
        data[trueIndex].$$treeLevel = 0;
        const { related } = data[trueIndex];
        const relatedIndex = trueIndex;
        let aggregations = {};
        for (let j = 0; j < related.length; ++j) {
          // eslint-disable-next-line no-loop-func
          const updated = Object.entries(related[j]).reduce((result, [key, value]) => {
            if (columnNamesToAggregate.includes(key)) aggregations[key] = (aggregations[key] ?? []).concat(value.split('; '));
            result[key] = value;
            return result;
          }, {});

          data.splice(++trueIndex, 0, _.pick(updated, visibleColumns));
        }

        aggregations = _.pickBy(
          _.mapValues(aggregations, (values, key) => {
            const col = findColumn(key);
            let cleanedValues = _.without(values, undefined, null, '');

            if (col.data_type === 'datetime') {
              cleanedValues = _.map(cleanedValues, (value) => $filter('date')(value, 'yyyy-MM-dd h:mm a'));
            }

            if (cleanedValues.length > 1) cleanedValues = _.uniq(cleanedValues);

            if (col.column_name === 'number_properties') {
              return _.sum(_.map(cleanedValues, _.toNumber)) || null;
            }
            if (cleanedValues.length === 1) return cleanedValues[0];
            return _.join(_.uniq(cleanedValues).sort(naturalSort), '; ');
          }),
          (result) => _.isNumber(result) || !_.isEmpty(result)
        );

        // Remove unnecessary data
        data[relatedIndex] = _.pick(data[relatedIndex], visibleColumns);
        // Insert aggregated child values into parent row
        _.merge(data[relatedIndex], aggregations);
      }
      $scope.data = data;
      $scope.updateQueued = true;
    };

    const fetchRecords = (page, chunk, ids_only = false) => {
      let fn;
      if ($scope.inventory_type === 'properties') {
        fn = inventory_service.get_properties;
      } else if ($scope.inventory_type === 'taxlots') {
        fn = inventory_service.get_taxlots;
      }

      // add label filtering
      let include_ids;
      let exclude_ids;

      if ($scope.selected_and_labels.length) {
        const intersection = _.intersection.apply(null, _.map($scope.selected_and_labels, 'is_applied'));
        include_ids = intersection.length ? intersection : [0];
      }
      if ($scope.selected_or_labels.length) {
        const union = _.union.apply(null, _.map($scope.selected_or_labels, 'is_applied'));
        if (include_ids !== undefined) {
          if (_.intersection(include_ids, union).length) {
            include_ids = _.intersection(include_ids, union);
          } else {
            include_ids = [0];
          }
        } else {
          include_ids = union;
        }
      }
      if ($scope.selected_exclude_labels.length) {
        exclude_ids = _.union.apply(null, _.map($scope.selected_exclude_labels, 'is_applied'));
      }

      return fn(
        page,
        chunk,
        $scope.cycle.selected_cycle,
        _.get($scope, 'currentProfile.id'),
        include_ids,
        exclude_ids,
        true,
        $scope.organization.id,
        true,
        $scope.column_filters,
        $scope.column_sorts,
        ids_only
      );
    };

    // evaluate all derived columns and add the results to the table
    const evaluateDerivedColumns = () => {
      const batch_size = 100;
      const batched_inventory_ids = [];
      let batch_index = 0;
      while (batch_index < $scope.data.length) {
        batched_inventory_ids.push($scope.data.slice(batch_index, batch_index + batch_size).map((d) => d.id));
        batch_index += batch_size;
      }

      // Find all columns that linked to a derived column.
      // With the associated derived columns evaluate it and attach it to the original column
      const visible_columns_with_derived_columns = $scope.columns.filter((col) => col.derived_column);
      const derived_column_ids = visible_columns_with_derived_columns.map((col) => col.derived_column);
      const attached_derived_columns = derived_columns_payload.derived_columns.filter((col) => derived_column_ids.includes(col.id));
      const column_name_lookup = {};
      visible_columns_with_derived_columns.forEach((col) => {
        column_name_lookup[col.column_name] = col.name;
      });

      const all_evaluation_results = [];
      for (const col of attached_derived_columns) {
        all_evaluation_results.push(
          ...batched_inventory_ids.map((ids) => derived_columns_service.evaluate($scope.organization.id, col.id, $scope.cycle.selected_cycle.id, ids).then((res) => {
            const formatted_results = res.results.map((x) => (typeof x.value === 'number' ? { ...x, value: _.round(x.value, $scope.organization.display_decimal_places) } : x));
            return { derived_column_id: col.id, results: formatted_results };
          }))
        );
      }

      $q.all(all_evaluation_results).then((results) => {
        const aggregated_results = {};
        results.forEach((result) => {
          if (result.derived_column_id in aggregated_results) {
            aggregated_results[result.derived_column_id].push(...result.results);
          } else {
            aggregated_results[result.derived_column_id] = result.results;
          }
        });

        // finally, update the data to include the calculated values
        $scope.data.forEach((row) => {
          Object.entries(aggregated_results).forEach(([derived_column_id, results]) => {
            const derived_column = attached_derived_columns.find((col) => col.id === Number(derived_column_id));
            const result = results.find((res) => res.id === row.id) || {};
            row[column_name_lookup[derived_column.name]] = result.value;
          });
        });
      });
    };

    $scope.load_inventory = (page) => {
      const page_size = 100;
      spinner_utility.show();
      return fetchRecords(page, page_size).then((data) => {
        if (data.status === 'error') {
          let { message } = data;
          if (data.recommended_action === 'update_column_settings') {
            const columnSettingsUrl = $state.href('organization_column_settings', { organization_id: $scope.organization.id, inventory_type: $scope.inventory_type });
            message = `${message}<br><a href="${columnSettingsUrl}">Click here to update your column settings</a>`;
          }
          Notification.error({ message, delay: 15000 });
          spinner_utility.hide();
          return;
        }
        $scope.inventory_pagination = data.pagination;
        processData(data.results);
        $scope.gridApi.core.notifyDataChange(uiGridConstants.dataChange.EDIT);
        evaluateDerivedColumns();
        $scope.select_none();
        spinner_utility.hide();
      });
    };

    $scope.filters_exist = () => !$scope.column_filters.length;

    $scope.sorts_exist = () => !$scope.column_sorts.length;

    // it appears resetColumnSorting() doesn't trigger on.sortChanged so we do it manually
    $scope.reset_column_sorting = () => {
      $scope.gridApi.grid.resetColumnSorting();
      $scope.gridApi.core.raise.sortChanged();
    };

    const get_labels = () => {
      label_service.get_labels($scope.inventory_type, undefined, $scope.cycle.selected_cycle.id).then((current_labels) => {
        $scope.labels = _.filter(current_labels, (label) => !_.isEmpty(label.is_applied));

        // load saved label filter
        let ids = inventory_service.loadSelectedLabels(localStorageLabelKey, 'and');
        $scope.selected_and_labels = _.filter($scope.labels, (label) => _.includes(ids, label.id));
        ids = inventory_service.loadSelectedLabels(localStorageLabelKey, 'or');
        $scope.selected_or_labels = _.filter($scope.labels, (label) => _.includes(ids, label.id));
        ids = inventory_service.loadSelectedLabels(localStorageLabelKey, 'exclude');
        $scope.selected_exclude_labels = _.filter($scope.labels, (label) => _.includes(ids, label.id));

        $scope.filterUsingLabels();
        $scope.build_labels();
      });
    };

    $scope.update_cycle = (cycle) => {
      inventory_service.save_last_cycle(cycle.id);
      $scope.cycle.selected_cycle = cycle;
      get_labels();
      $scope.load_inventory(1);
    };

    $scope.open_ubid_decode_modal = (selectedViewIds) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/ubid_decode_modal.html`,
        controller: 'ubid_decode_modal_controller',
        resolve: {
          property_view_ids: () => ($scope.inventory_type === 'properties' ? selectedViewIds : []),
          taxlot_view_ids: () => ($scope.inventory_type === 'taxlots' ? selectedViewIds : [])
        }
      });
    };

    $scope.open_ubid_jaccard_index_modal = (selectedViewIds) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/ubid_jaccard_index_modal.html`,
        controller: 'ubid_jaccard_index_modal_controller',
        backdrop: 'static',
        resolve: {
          ubids: () => {
            if (!selectedViewIds.length) {
              return [];
            }
            let ubid_column;
            let promise;
            if ($scope.inventory_type === 'properties') {
              promise = inventory_service.get_mappable_property_columns().then((columns) => {
                ubid_column = columns.find((c) => c.column_name === 'ubid');
                return inventory_service.get_properties(1, undefined, undefined, -1, selectedViewIds);
              });
            } else {
              promise = inventory_service.get_mappable_taxlot_columns().then((columns) => {
                ubid_column = columns.find((c) => c.column_name === 'ubid');
                return inventory_service.get_taxlots(1, undefined, undefined, -1, selectedViewIds);
              });
            }
            return promise.then((inventory_data) => inventory_data.results.map((d) => d[ubid_column.name]));
          }
        }
      });
    };

    $scope.open_ubid_admin_modal = (selectedViewId) => {
      $uibModal.open({
        backdrop: 'static',
        templateUrl: `${urls.static_url}seed/partials/ubid_admin_modal.html`,
        controller: 'ubid_admin_modal_controller',
        resolve: {
          property_view_id: () => ($scope.inventory_type === 'properties' ? selectedViewId[0] : null),
          taxlot_view_id: () => ($scope.inventory_type === 'taxlots' ? selectedViewId[0] : null),
          inventory_payload: [
            '$state',
            '$stateParams',
            'inventory_service',
            ($state, $stateParams, inventory_service) => ($scope.inventory_type === 'properties' ? inventory_service.get_property(selectedViewId[0]) : inventory_service.get_taxlot(selectedViewId[0]))
          ]
        }
      });
    };

    $scope.open_geocode_modal = (selectedViewIds) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/geocode_modal.html`,
        controller: 'geocode_modal_controller',
        resolve: {
          property_view_ids: () => ($scope.inventory_type === 'properties' ? selectedViewIds : []),
          taxlot_view_ids: () => ($scope.inventory_type === 'taxlots' ? selectedViewIds : []),
          org_id: () => $scope.organization.id,
          inventory_type: () => $scope.inventory_type
        }
      });

      modalInstance.result.then((/* result */) => {
        // dialog was closed with 'Close' button.
        $scope.load_inventory(1);
      });
    };

    $scope.open_delete_modal = (selectedViewIds) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/delete_modal.html`,
        controller: 'delete_modal_controller',
        resolve: {
          property_view_ids: () => ($scope.inventory_type === 'properties' ? selectedViewIds : []),
          taxlot_view_ids: () => ($scope.inventory_type === 'taxlots' ? selectedViewIds : [])
        }
      });

      modalInstance.result.then(
        (result) => {
          if (_.includes(['fail', 'incomplete'], result.delete_state)) $scope.load_inventory(1);
          else if (result.delete_state === 'success') {
            const selectedRows = $scope.gridApi.selection.getSelectedRows();
            const selectedChildRows = _.remove(selectedRows, (row) => !_.has(row, '$$treeLevel'));
            // Delete selected child rows first
            _.forEach(selectedChildRows, (row) => {
              const index = $scope.data.lastIndexOf(row);
              let count = 1;
              if (row.$$treeLevel === 0) {
                // Count children to delete
                let i = index + 1;
                while (i < $scope.data.length - 1 && !_.has($scope.data[i], '$$treeLevel')) {
                  count++;
                  i++;
                }
              }
              // console.debug('Deleting ' + count + ' child rows');
              $scope.data.splice(index, count);
            });
            // Delete parent rows and all child rows
            _.forEach(selectedRows, (row) => {
              const index = $scope.data.lastIndexOf(row);
              let count = 1;
              if (row.$$treeLevel === 0) {
                // Count children to delete
                let i = index + 1;
                while (i < $scope.data.length - 1 && !_.has($scope.data[i], '$$treeLevel')) {
                  count++;
                  i++;
                }
              }
              // console.debug('Deleting ' + count + ' rows');
              $scope.data.splice(index, count);
            });
            // Delete any child rows that may have been duplicated due to a M2M relationship
            if ($scope.inventory_type === 'properties') {
              _.remove($scope.data, (row) => !_.has(row, '$$treeLevel') && _.includes(result.taxlot_states, row.taxlot_state_id));
            } else if ($scope.inventory_type === 'taxlots') {
              _.remove($scope.data, (row) => !_.has(row, '$$treeLevel') && _.includes(result.property_states, row.property_state_id));
            }
            $scope.load_inventory(1);
          }
        },
        (result) => {
          if (_.includes(['fail', 'incomplete'], result.delete_state)) $scope.load_inventory(1);
        }
      );
    };

    $scope.updateHeight = () => {
      let height = 0;
      _.forEach(['.header', '.page_header_container', '.section_nav_container', '.inventory-list-controls', '.inventory-list-tab-container'], (selector) => {
        const element = angular.element(selector)[0];
        if (element) height += element.offsetHeight;
      });
      angular.element('#grid-container').css('height', `calc(100vh - ${height - 1}px)`);
      $scope.gridApi.core.handleWindowResize();
    };

    $scope.open_export_modal = (selectedViewIds) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/export_inventory_modal.html`,
        controller: 'export_inventory_modal_controller',
        resolve: {
          ids: () => selectedViewIds,
          filter_header_string() {
            if ($scope.selected_and_labels.length || $scope.selected_or_labels.length || $scope.selected_exclude_labels.length) {
              return [
                'Must Have Filter Labels: "',
                $scope.selected_and_labels.map((label) => label.name).join(' - '),
                '",Include Any Filter Labels: "',
                $scope.selected_or_labels.map((label) => label.name).join(' - '),
                '",Exclude Filter Labels: "',
                $scope.selected_exclude_labels.map((label) => label.name).join(' - '),
                '"'
              ].join('');
            }
            return 'Filter Labels: ""none""';
          },
          columns: () => _.map($scope.columns, 'name'),
          inventory_type: () => $scope.inventory_type,
          profile_id() {
            // Check to see if the profile id is set
            if ($scope.currentProfile) {
              return $scope.currentProfile.id;
            }
            return null;
          }
        }
      });
    };

    $scope.open_export_to_audit_template_modal = (selectedViewIds) => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/export_to_audit_template_modal.html`,
        controller: 'export_to_audit_template_modal_controller',
        resolve: {
          ids: () => selectedViewIds,
          org_id: () => $scope.organization.id
        }
      });
    };

    $scope.model_actions = 'none';
    const elSelectActions = document.getElementById('select-actions');
    $scope.run_action = (viewIds = [], action = null) => {
      let selectedViewIds = [];

      // was the function called with a list of ids?
      if (viewIds.length > 0) {
        selectedViewIds = viewIds;

        // if it appears everything selected, only get the full set of ids...
      } else if ($scope.selectedCount >= $scope.inventory_pagination.total && $scope.inventory_pagination.num_pages > 1) {
        selectedViewIds = [];

        if ($scope.inventory_type === 'properties') {
          selectedViewIds = fetchRecords(undefined, undefined, true).then((inventory_data) => {
            $scope.run_action(inventory_data.results);
          });
        } else if ($scope.inventory_type === 'taxlots') {
          selectedViewIds = fetchRecords(undefined, undefined, true).then((inventory_data) => {
            $scope.run_action(inventory_data.results);
          });
        }
        return;

        // ... otherwise use what's selected in the grid
      } else {
        const view_id_prop = $scope.inventory_type === 'taxlots' ? 'taxlot_view_id' : 'property_view_id';
        selectedViewIds = _.map(_.filter($scope.gridApi.selection.getSelectedRows(), { $$treeLevel: 0 }), view_id_prop);
      }

      if (!action) {
        action = elSelectActions.value;
      }
      switch (action) {
        case 'open_merge_modal':
          $scope.open_merge_modal(selectedViewIds);
          break;
        case 'open_delete_modal':
          $scope.open_delete_modal(selectedViewIds);
          break;
        case 'open_export_modal':
          $scope.open_export_modal(selectedViewIds);
          break;
        case 'open_export_to_audit_template_modal':
          $scope.open_export_to_audit_template_modal(selectedViewIds);
          break;
        case 'open_update_labels_modal':
          $scope.open_update_labels_modal(selectedViewIds);
          break;
        case 'run_data_quality_check':
          $scope.run_data_quality_check(selectedViewIds);
          break;
        case 'open_postoffice_modal':
          $scope.open_postoffice_modal(selectedViewIds);
          break;
        case 'open_analyses_modal':
          $scope.open_analyses_modal(selectedViewIds);
          break;
        case 'open_set_update_to_now_modal':
          $scope.open_set_update_to_now_modal(selectedViewIds);
          break;
        case 'open_geocode_modal':
          $scope.open_geocode_modal(selectedViewIds);
          break;
        case 'open_ubid_jaccard_index_modal':
          $scope.open_ubid_jaccard_index_modal(selectedViewIds);
          break;
        case 'open_ubid_decode_modal':
          $scope.open_ubid_decode_modal(selectedViewIds);
          break;
        case 'open_ubid_admin_modal':
          $scope.open_ubid_admin_modal(selectedViewIds);
          break;
        case 'open_show_populated_columns_modal':
          $scope.open_show_populated_columns_modal();
          break;
        case 'toggle_access_level_instances':
          $scope.toggle_access_level_instances();
          break;
        case 'select_all':
          $scope.select_all();
          break;
        case 'select_none':
          $scope.select_none();
          break;
        case 'update_salesforce':
          $scope.update_salesforce(selectedViewIds);
          break;
        default:
          console.error('Unknown action:', elSelectActions.value, 'Update "run_action()"');
      }
      $scope.model_actions = 'none';
    };

    $scope.open_set_update_to_now_modal = () => {
      const primary_rows = $scope.gridApi.selection.getSelectedRows().filter((r) => r.$$treeLevel === 0);
      const secondary_rows = $scope.gridApi.selection.getSelectedRows().filter((r) => r.$$treeLevel === undefined);

      let property_rows;
      let taxlot_rows;
      if ($scope.inventory_type === 'properties') {
        property_rows = primary_rows;
        taxlot_rows = secondary_rows;
      } else {
        taxlot_rows = primary_rows;
        property_rows = secondary_rows;
      }

      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/set_update_to_now_modal.html`,
        controller: 'set_update_to_now_modal_controller',
        backdrop: 'static',
        resolve: {
          property_views: () => [...new Set(property_rows.map((r) => r.property_view_id))],
          taxlot_views: () => [...new Set(taxlot_rows.map((r) => r.taxlot_view_id))]
        }
      });
    };

    $scope.open_analyses_modal = (selectedViewIds) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/inventory_detail_analyses_modal.html`,
        controller: 'inventory_detail_analyses_modal_controller',
        resolve: {
          inventory_ids: () => ($scope.inventory_type === 'properties' ? selectedViewIds : []),
          cycles: () => cycles.cycles,
          current_cycle: () => $scope.cycle.selected_cycle,
          user: () => $scope.menu.user
        }
      });
      modalInstance.result.then(
        () => {
          setTimeout(() => {
            Notification.primary('<a href="#/analyses" style="color: #337ab7;">Click here to view your analyses</a>');
          }, 1000);
        },
        () => {
          // Modal dismissed, do nothing
        }
      );
    };

    $scope.update_salesforce = (selectedViewIds) => {
      inventory_service
        .update_salesforce(selectedViewIds)
        .then(() => {
          Notification.success({ message: 'Salesforce Update Successful!', delay: 5000 });
        })
        .catch((result) => {
          Notification.error({ message: `Error updating Salesforce: ${result.data.message}`, delay: 15000, closeOnClick: true });
        });
    };

    $scope.view_notes = (record) => {
      $uibModal
        .open({
          templateUrl: `${urls.static_url}seed/partials/notes_modal.html`,
          controller: 'notes_controller',
          size: 'lg',
          resolve: {
            inventory_type: () => record.inventory_type,
            view_id: () => record.view_id,
            inventory_payload: [
              '$state',
              '$stateParams',
              'inventory_service',
              ($state, $stateParams, inventory_service) => (record.inventory_type === 'properties' ? inventory_service.get_property(record.view_id) : inventory_service.get_taxlot(record.view_id))
            ],
            organization_payload: () => organization_payload,
            notes: ['note_service', (note_service) => note_service.get_notes($scope.organization.id, record.inventory_type, record.view_id)],
            auth_payload: [
              'auth_service',
              'user_service',
              (auth_service, user_service) => {
                const organization_id = user_service.get_organization().id;
                return auth_service.is_authorized(organization_id, ['requires_member']);
              }
            ]
          }
        })
        .result.then((notes_count) => {
          record.record.notes_count = notes_count;
        });
    };

    function currentColumns() {
      // Save all columns except first 3 and Access Level Instances
      let gridCols = _.filter(
        $scope.gridApi.grid.columns,
        (col) => !_.includes(['treeBaseRowHeaderCol', 'selectionRowHeaderCol', 'notes_count', 'meters_exist_indicator', 'merged_indicator', 'id', 'labels'], col.name) &&
          col.visible &&
          !col.colDef.is_derived_column &&
          col.colDef.group !== 'access_level_instance'
      );

      // Ensure pinned ordering first
      const pinned = _.remove(gridCols, (col) => col.renderContainer === 'left');
      gridCols = pinned.concat(gridCols);

      const columns = [];
      _.forEach(gridCols, (col) => {
        columns.push({
          column_name: col.colDef.column_name,
          id: col.colDef.id,
          order: columns.length + 1,
          pinned: col.renderContainer === 'left',
          table_name: col.colDef.table_name
        });
      });

      return columns;
    }

    const saveSettings = () => {
      if (!profiles.length) {
        // Create a profile first
        $scope.newProfile().then(() => {
          const { id } = $scope.currentProfile;
          const profile = _.omit($scope.currentProfile, 'id');
          profile.columns = currentColumns();
          inventory_service.update_column_list_profile(id, profile);
        });
      } else {
        const { id } = $scope.currentProfile;
        const profile = _.omit($scope.currentProfile, 'id');
        profile.columns = currentColumns();
        inventory_service.update_column_list_profile(id, profile);
      }
    };

    $scope.selected_display = '';
    $scope.update_selected_display = () => {
      if ($scope.gridApi && $scope.gridApi.grid.gridMenuScope) {
        uiGridGridMenuService.removeFromGridMenu($scope.gridApi.grid, 'dynamic-export');
        $scope.gridApi.core.addToGridMenu($scope.gridApi.grid, [
          {
            id: 'dynamic-export',
            title: $scope.selectedCount === 0 ? 'Export All' : 'Export Selected',
            order: 100,
            action() {
              $scope.run_action([], 'open_export_modal');
            }
          }
        ]);
      }
      $scope.selected_display = [$scope.selectedCount, $translate.instant('selected')].join(' ');
    };
    $scope.update_selected_display();

    const operatorLookup = {
      ne: '!=',
      exact: '=',
      lt: '<',
      lte: '<=',
      gt: '>',
      gte: '>=',
      icontains: ''
    };
    const operatorArr = ['>', '<', '=', '!', '!=', '<=', '>='];

    $scope.delete_filter = (filterToDelete) => {
      const column = $scope.gridApi.grid.getColumn(filterToDelete.name);
      if (!column || column.filters.size < 1) {
        return false;
      }
      const newTerm = [];
      for (const i in $scope.column_filters) {
        const filter = $scope.column_filters[i];
        if (filter.name !== filterToDelete.name || filter === filterToDelete) {
          continue;
        }
        newTerm.push(operatorLookup[filter.operator] + filter.value);
      }
      column.filters[0].term = newTerm.join(', ');
      return false;
    };

    $scope.delete_sort = (sortToDelete) => {
      $scope.gridApi.grid.getColumn(sortToDelete.name).unsort();
      return true;
    };

    // https://regexr.com/6cka2
    const combinedRegex = /^(!?)=\s*(-?\d+(?:\.\d+)?)$|^(!?)=?\s*"((?:[^"]|\\")*)"$|^(<=?|>=?)\s*((-?\d+(?:\.\d+)?)|(\d{4}-\d{2}-\d{2}))$/;
    const parseFilter = (expression) => {
      // parses an expression string into an object containing operator and value
      const filterData = expression.match(combinedRegex);
      if (filterData) {
        if (!_.isUndefined(filterData[2])) {
          // Numeric Equality
          const operator = filterData[1];
          const value = Number(filterData[2].replace('\\.', '.'));
          if (operator === '!') {
            return { string: 'is not', operator: 'ne', value };
          }
          return { string: 'is', operator: 'exact', value };
        }
        if (!_.isUndefined(filterData[4])) {
          // Text Equality
          const operator = filterData[3];
          const value = filterData[4];
          if (operator === '!') {
            return { string: 'is not', operator: 'ne', value };
          }
          return { string: 'is', operator: 'exact', value };
        }
        if (!_.isUndefined(filterData[7])) {
          // Numeric Comparison
          const operator = filterData[5];
          const value = Number(filterData[6].replace('\\.', '.'));
          switch (operator) {
            case '<':
              return { string: '<', operator: 'lt', value };
            case '<=':
              return { string: '<=', operator: 'lte', value };
            case '>':
              return { string: '>', operator: 'gt', value };
            case '>=':
              return { string: '>=', operator: 'gte', value };
          }
        } else {
          // Date Comparison
          const operator = filterData[5];
          const value = filterData[8];
          switch (operator) {
            case '<':
              return { string: '<', operator: 'lt', value };
            case '<=':
              return { string: '<=', operator: 'lte', value };
            case '>':
              return { string: '>', operator: 'gt', value };
            case '>=':
              return { string: '>=', operator: 'gte', value };
          }
        }
      } else {
        // Case-insensitive Contains
        return { string: 'contains', operator: 'icontains', value: expression };
      }
    };

    const updateColumnFilterSort = () => {
      const columns = _.filter($scope.gridApi.saveState.save().columns, (col) => _.keys(col.sort).filter((key) => key !== 'ignoreSort').length + (_.get(col, 'filters[0].term', '') || '').length > 0);

      inventory_service.saveGridSettings(`${localStorageKey}.sort`, {
        columns
      });

      $scope.column_filters = [];
      $scope.column_sorts = [];
      // parse the filters and sorts
      for (const column of columns) {
        const { name, filters, sort } = column;
        // remove the column id at the end of the name
        const column_name = name.split('_').slice(0, -1).join('_');

        for (const filter of filters) {
          if (_.isEmpty(filter)) {
            continue;
          }

          // a filter can contain many comma-separated filters
          const subFilters = _.map(_.split(filter.term, ','), _.trim);
          for (const subFilter of subFilters) {
            if (subFilter) {
              // ignore filters with only an operator. user is not done typing
              if (operatorArr.includes(subFilter)) {
                continue;
              }

              const { string, operator, value } = parseFilter(subFilter);
              const display = [$scope.columnDisplayByName[name], string, value].join(' ');
              $scope.column_filters.push({
                name,
                column_name,
                operator,
                value,
                display
              });
            }
          }
        }

        if (sort.direction) {
          // remove the column id at the end of the name
          const column_name = name.split('_').slice(0, -1).join('_');
          const display = [$scope.columnDisplayByName[name], sort.direction].join(' ');
          $scope.column_sorts.push({
            name,
            column_name,
            direction: sort.direction,
            display,
            priority: sort.priority
          });
          $scope.column_sorts.sort((a, b) => a.priority > b.priority);
        }
      }
      $scope.isModified();
    };

    const restoreGridSettings = () => {
      $scope.restore_status = RESTORE_SETTINGS;
      let state = inventory_service.loadGridSettings(`${localStorageKey}.sort`);
      // If save state has filters or sorts, ignore the grids first attempt to run filterChanged or sortChanged
      const { columns } = JSON.parse(state) ?? {};
      $scope.ignore_filter_or_sort = !_.isEmpty(columns);
      if (!_.isNull(state)) {
        state = JSON.parse(state);
        $scope.gridApi.saveState.restore($scope, state).then(() => {
          $scope.restore_status = RESTORE_SETTINGS_DONE;
        });
      } else {
        $scope.restore_status = RESTORE_SETTINGS_DONE;
      }
    };

    $scope.select_all = () => {
      // select all rows to visibly support everything has been selected
      $scope.gridApi.selection.selectAllRows();
      $scope.selectedCount = $scope.inventory_pagination.total;
      $scope.update_selected_display();
    };

    $scope.select_none = () => {
      $scope.gridApi.selection.clearSelectedRows();
      $scope.selectedCount = 0;
      $scope.update_selected_display();
    };

    const filterOrSortChanged = _.debounce(() => {
      if ($scope.ignore_filter_or_sort) {
        $scope.ignore_filter_or_sort = false;
      } else if ($scope.restore_status === RESTORE_COMPLETE) {
        updateColumnFilterSort();
        $scope.load_inventory(1);
      }
    }, 1000);

    $scope.gridOptions = {
      data: 'data',
      enableFiltering: true,
      enableGridMenu: true,
      enableSorting: true,
      exporterMenuCsv: false,
      exporterMenuExcel: false,
      exporterMenuPdf: false,
      fastWatch: true,
      flatEntityAccess: true,
      gridMenuShowHideColumns: false,
      hidePinRight: true,
      saveFocus: false,
      saveGrouping: false,
      saveGroupingExpandedStates: false,
      saveOrder: false,
      savePinning: false,
      saveScroll: false,
      saveSelection: false,
      saveTreeView: false,
      saveVisible: false,
      saveWidths: false,
      showTreeExpandNoChildren: false,
      useExternalFiltering: true,
      useExternalSorting: true,
      columnDefs: $scope.columns,
      onRegisterApi(gridApi) {
        $scope.gridApi = gridApi;

        _.delay($scope.updateHeight, 150);

        const debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
        angular.element($window).on('resize', debouncedHeightUpdate);
        $scope.$on('$destroy', () => {
          angular.element($window).off('resize', debouncedHeightUpdate);
        });

        gridApi.colMovable.on.columnPositionChanged($scope, () => {
          // Ensure that 'merged_indicator', 'notes_count', 'meters_exist_indicator', and 'id' remain first
          let col;
          let staticColIndex;
          staticColIndex = _.findIndex($scope.gridApi.grid.columns, { name: 'merged_indicator' });
          if (staticColIndex !== 2) {
            col = $scope.gridApi.grid.columns[staticColIndex];
            $scope.gridApi.grid.columns.splice(staticColIndex, 1);
            $scope.gridApi.grid.columns.splice(2, 0, col);
          }
          staticColIndex = _.findIndex($scope.gridApi.grid.columns, { name: 'notes_count' });
          if (staticColIndex !== 3) {
            col = $scope.gridApi.grid.columns[staticColIndex];
            $scope.gridApi.grid.columns.splice(staticColIndex, 1);
            $scope.gridApi.grid.columns.splice(3, 0, col);
          }
          staticColIndex = _.findIndex($scope.gridApi.grid.columns, { name: 'meters_exist_indicator' });
          if (staticColIndex !== 4) {
            col = $scope.gridApi.grid.columns[staticColIndex];
            $scope.gridApi.grid.columns.splice(staticColIndex, 1);
            $scope.gridApi.grid.columns.splice(4, 0, col);
          }
          staticColIndex = _.findIndex($scope.gridApi.grid.columns, { name: 'id' });
          if (staticColIndex !== 5) {
            col = $scope.gridApi.grid.columns[staticColIndex];
            $scope.gridApi.grid.columns.splice(staticColIndex, 1);
            $scope.gridApi.grid.columns.splice(5, 0, col);
          }
          saveSettings();
        });
        gridApi.core.on.columnVisibilityChanged($scope, saveSettings);
        gridApi.core.on.filterChanged($scope, filterOrSortChanged);
        gridApi.core.on.sortChanged($scope, filterOrSortChanged);
        gridApi.pinning.on.columnPinned($scope, (colDef, container) => {
          if (container) {
            saveSettings();
          } else {
            // Hack to fix disappearing filter after unpinning a column
            const gridCol = gridApi.grid.columns.find(({ colDef: { name } }) => name === colDef.name);
            if (gridCol) {
              gridCol.colDef.visible = false;
              gridApi.grid.refresh();

              $timeout(() => {
                gridCol.colDef.visible = true;
                gridApi.grid.refresh();
                saveSettings();
              }, 0);
            }
          }
        });

        const selectionChanged = () => {
          const selected = gridApi.selection.getSelectedRows();
          const parentsSelectedIds = _.map(_.filter(selected, { $$treeLevel: 0 }), 'id');
          $scope.selectedCount = selectionLengthByInventoryType(selected);
          $scope.selectedParentCount = parentsSelectedIds.length;

          const removed = _.difference($scope.selectedOrder, parentsSelectedIds);
          const added = _.difference(parentsSelectedIds, $scope.selectedOrder);
          if (removed.length === 1 && !added.length) {
            _.remove($scope.selectedOrder, (item) => item === removed[0]);
          } else if (added.length === 1 && !removed.length) {
            $scope.selectedOrder.push(added[0]);
          }
          $scope.update_selected_display();
        };

        const selectPageChanged = () => {
          const allSelected = $scope.gridApi.selection.getSelectedRows();

          if (!allSelected.length) {
            $scope.selectedCount = 0;
            $scope.selectedParentCount = 0;
            $scope.selectedOrder = [];
          } else {
            const parentsSelectedIds = _.map(_.filter(allSelected, { $$treeLevel: 0 }), 'id');
            const sortedIds = _.map($scope.gridApi.core.getVisibleRows($scope.gridApi.grid), (row) => row.entity.id);
            $scope.selectedOrder = _.filter(sortedIds, (id) => _.includes(parentsSelectedIds, id));
            $scope.selectedCount = selectionLengthByInventoryType(allSelected);
            $scope.selectedParentCount = parentsSelectedIds.length;
          }
          $scope.update_selected_display();
        };

        const selectionLengthByInventoryType = (selection) => ($scope.inventory_type === 'properties' ?
          selection.filter((item) => item.property_state_id || item.property_view_id).length :
          selection.filter((item) => item.taxlot_state_id || item.taxlot_view_id).length);

        gridApi.selection.on.rowSelectionChanged($scope, selectionChanged);
        gridApi.selection.on.rowSelectionChangedBatch($scope, selectPageChanged);

        gridApi.core.on.rowsRendered(
          $scope,
          _.debounce(() => {
            $scope.$apply(() => {
              spinner_utility.hide();
              $scope.total = _.filter($scope.gridApi.core.getVisibleRows($scope.gridApi.grid), { treeLevel: 0 }).length;
              if ($scope.updateQueued) {
                $scope.updateQueued = false;
              }
            });
          }, 150)
        );

        _.defer(() => {
          restoreGridSettings();
        });
      }
    };
  }
]);
