/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail', []).controller('inventory_detail_controller', [
  '$http',
  '$state',
  '$scope',
  '$uibModal',
  '$log',
  '$filter',
  '$stateParams',
  '$anchorScroll',
  '$location',
  '$window',
  '$q',
  'uiGridConstants',
  'Notification',
  'urls',
  'spinner_utility',
  'label_service',
  'inventory_service',
  'matching_service',
  'pairing_service',
  'derived_columns_service',
  'organization_service',
  'dataset_service',
  'inventory_payload',
  'views_payload',
  'analyses_payload',
  // 'users_payload',
  'columns',
  'derived_columns_payload',
  'profiles',
  'current_profile',
  'labels_payload',
  'organization_payload',
  'cycle_service',
  'simple_modal_service',
  'property_measure_service',
  'scenario_service',
  // eslint-disable-next-line func-names
  function (
    $http,
    $state,
    $scope,
    $uibModal,
    $log,
    $filter,
    $stateParams,
    $anchorScroll,
    $location,
    $window,
    $q,
    uiGridConstants,
    Notification,
    urls,
    spinner_utility,
    label_service,
    inventory_service,
    matching_service,
    pairing_service,
    derived_columns_service,
    organization_service,
    dataset_service,
    inventory_payload,
    views_payload,
    analyses_payload,
    // users_payload,
    columns,
    derived_columns_payload,
    profiles,
    current_profile,
    labels_payload,
    organization_payload,
    cycle_service,
    simple_modal_service,
    property_measure_service,
    scenario_service
  ) {
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.organization = organization_payload.organization;

    // WARNING: $scope.org is used by "child" controller - analysis_details_controller
    $scope.org = { id: organization_payload.organization.id };
    $scope.static_url = urls.static_url;
    $scope.show_at_scenario_actions = true;

    // Detail Column List Profile
    $scope.profiles = profiles;
    $scope.currentProfile = current_profile;

    $scope.inventory = {
      view_id: $stateParams.view_id,
      related: $scope.inventory_type === 'properties' ? inventory_payload.taxlots : inventory_payload.properties
    };
    $scope.cycle = inventory_payload.cycle;
    $scope.cycles = [$scope.cycle];

    let ignoreNextChange = true;

    views_payload = $scope.inventory_type === 'properties' ? views_payload.property_views : views_payload.taxlot_views;
    $scope.views = views_payload
      .map(({ id, cycle }) => ({
        view_id: id,
        cycle_name: cycle.name
      }))
      .sort((a, b) => a.cycle_name.localeCompare(b.cycle_name));
    $scope.selected_view = $scope.views.find(({ view_id }) => view_id === $scope.inventory.view_id);

    $scope.changeView = () => {
      window.location.href = `/app/#/${$scope.inventory_type}/${$scope.selected_view.view_id}`;
    };

    $scope.labels = _.filter(labels_payload, (label) => !_.isEmpty(label.is_applied));
    $scope.audit_template_building_id = inventory_payload.state.audit_template_building_id;
    $scope.pm_property_id = inventory_payload.state.pm_property_id;

    /** See service for structure of returned payload */
    $scope.historical_items = inventory_payload.history;
    $scope.item_state = inventory_payload.state;
    $scope.inventory_docs = $scope.inventory_type === 'properties' ? inventory_payload.property.inventory_documents : null;
    const ali = $scope.inventory_type === 'properties' ?
      inventory_payload.property.access_level_instance :
      inventory_payload.taxlot.access_level_instance;

    $scope.ali_path = {};
    if (typeof ali === 'object') {
      $scope.ali_path = ali.path;
    }

    $scope.order_historical_items_with_scenarios = () => {
      $scope.historical_items_with_scenarios = $scope.historical_items ? $scope.historical_items.filter((item) => !_.isEmpty(item.state.scenarios)) : [];
      $scope.historical_items_with_scenarios.sort((a, b) => {
        const dateA = a.state.extra_data.audit_date ? new Date(a.state.extra_data.audit_date) : 1;
        const dateB = b.state.extra_data.audit_date ? new Date(b.state.extra_data.audit_date) : 1;
        return dateB - dateA;
      });
    };
    $scope.order_historical_items_with_scenarios();
    $scope.format_epoch = (epoch) => moment(epoch).format('YYYY-MM-DD');

    // stores derived column values -- updated later once we fetch the data
    $scope.item_derived_values = {};

    $scope.inventory_display_name = organization_service.get_inventory_display_value($scope.organization, $scope.inventory_type === 'properties' ? 'property' : 'taxlot', $scope.item_state);

    // item_parent is the property or the tax lot instead of the PropertyState / TaxLotState
    if ($scope.inventory_type === 'properties') {
      $scope.item_parent = inventory_payload.property;
    } else {
      $scope.item_parent = inventory_payload.taxlot;
    }

    if (analyses_payload.analyses) {
      const cycle_analyses = analyses_payload.analyses.filter((analysis) => analysis.cycles.includes($scope.cycle.id));
      $scope.analysis = cycle_analyses.sort((a, b) => {
        const key_a = new Date(a.end_time);
        const key_b = new Date(b.end_time);
        if (key_a > key_b) return -1;
        if (key_a < key_b) return 1;
        return 0;
      })[0];
    }
    // $scope.users = users_payload.users;

    // handle popovers cleared on scrolling
    [document.getElementsByClassName('ui-view-container')[0], document.getElementById('pin')].forEach((el) => {
      if (el) el.onscroll = document.body.click;
    });

    // Flag columns whose values have changed between imports and edits.
    const historical_states = _.map($scope.historical_items, 'state');

    const historical_changes_check = (column) => {
      let uniq_column_values;
      const states = historical_states.concat($scope.item_state);

      if (column.is_extra_data) {
        uniq_column_values = _.uniqBy(
          states,
          // Normalize missing column_name keys returning undefined to return null.
          (state) => state.extra_data[column.column_name] || null
        );
      } else {
        uniq_column_values = _.uniqBy(states, column.column_name);
      }

      column.changed = uniq_column_values.length > 1;
      return column;
    };

    if ($scope.currentProfile) {
      $scope.columns = [];
      // add columns
      _.forEach($scope.currentProfile.columns, (col) => {
        const foundCol = _.find(columns, { id: col.id });
        if (foundCol) $scope.columns.push(historical_changes_check(foundCol));
      });
    } else {
      // No profiles exist
      $scope.columns = _.reject(columns, 'is_extra_data');
    }

    const profile_formatted_columns = () => _.map($scope.columns, (col, index) => ({
      column_name: col.column_name,
      id: col.id,
      order: index + 1,
      pinned: false,
      table_name: col.table_name
    }));

    $scope.newProfile = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/settings_profile_modal.html`,
        controller: 'settings_profile_modal_controller',
        resolve: {
          action: () => 'new',
          data: () => ({
            columns: profile_formatted_columns(),
            derived_columns: []
          }),
          profile_location: () => 'Detail View Profile',
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

    const populated_columns_modal = () => {
      $uibModal.open({
        backdrop: 'static',
        templateUrl: `${urls.static_url}seed/partials/show_populated_columns_modal.html`,
        controller: 'show_populated_columns_modal_controller',
        resolve: {
          columns: () => columns,
          currentProfile: () => $scope.currentProfile,
          cycle: () => null,
          inventory_type: () => $stateParams.inventory_type,
          provided_inventory() {
            const provided_inventory = [];

            // Add historical items
            _.each($scope.historical_items, (item) => {
              const item_state_copy = angular.copy(item.state);
              _.defaults(item_state_copy, item.state.extra_data);
              provided_inventory.push(item_state_copy);
            });

            // add "master" copy
            const item_copy = angular.copy($scope.item_state);
            _.defaults(item_copy, $scope.item_state.extra_data);

            return provided_inventory;
          }
        }
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

    $scope.open_doc_upload_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/document_upload_modal.html`,
        controller: 'document_upload_modal_controller',
        resolve: {
          organization_id: () => $scope.organization.id,
          view_id: () => $scope.inventory.view_id
        }
      });
    };

    $scope.isDisabledField = (name) => _.includes(['geocoding_confidence', 'created', 'updated'], name);

    // The server provides of *all* extra_data keys (across current state and all historical state)
    // Let's remember this.
    $scope.all_extra_data_keys = inventory_payload.extra_data_keys;

    $scope.user = {};
    $scope.user_role = inventory_payload.user_role;

    $scope.edit_form_showing = false;

    /** Holds a copy of original state of item_state.
     *  Used when 'Cancel' is selected and item should be
     *  returned to original state. */
    $scope.item_copy = {};

    /** An array of fields to show to user,
     *  populated according to settings. */
    $scope.data_fields = [];

    $scope.status = {
      isopen: false
    };

    $scope.$watch('currentProfile', (newProfile) => {
      if (ignoreNextChange) {
        ignoreNextChange = false;
        return;
      }

      inventory_service.save_last_detail_profile(newProfile.id, $scope.inventory_type);
      spinner_utility.show();
      $window.location.reload();
    });

    $scope.gotoMeasureAnchor = (x) => {
      $location.hash(`measureAnchor${x}`);
      $anchorScroll();
    };

    $scope.init_labels = (item) => _.map(item.labels, (lbl) => {
      lbl.label = label_service.lookup_label(lbl.color);
      return lbl;
    });

    /* User clicked 'cancel' button */
    $scope.on_cancel = () => {
      $scope.restore_copy();
      $scope.edit_form_showing = false;
    };

    /* User clicked 'edit' link */
    $scope.on_edit = () => {
      $scope.make_copy_before_edit();
      $scope.edit_form_showing = true;
    };

    /**
     * save_property_state: saves the property state in case cancel gets clicked
     */
    $scope.make_copy_before_edit = () => {
      $scope.item_copy = angular.copy($scope.item_state);
    };

    /**
     * restore_property: restores the property state from its copy
     */
    $scope.restore_copy = () => {
      $scope.item_state = $scope.item_copy;
    };

    /**
     * is_valid_key: checks to see if the key or attribute should be excluded
     *   from being copied from parent to master building
     *
     *    TODO Update these for v2...I've removed keys that were obviously old (e.g., canonical)
     */
    $scope.is_valid_data_column_key = (key) => {
      const known_invalid_keys = [
        'children',
        'confidence',
        'created',
        'extra_data',
        'extra_data_sources',
        'id',
        'is_master',
        'import_file',
        'import_file_name',
        'last_modified_by',
        'match_type',
        'modified',
        'model',
        'parents',
        'pk',
        'super_organization',
        'source_type',
        'duplicate'
      ];
      const no_invalid_key = !_.includes(known_invalid_keys, key);

      return !_.includes(key, '_source') && !_.includes(key, 'extra_data') && !_.includes(key, '$$') && no_invalid_key;
    };

    /**
     * returns a number
     */
    $scope.get_number = (num) => {
      if (!angular.isNumber(num) && !_.isNil(num)) {
        return +num.replace(/,/g, '');
      }
      return num;
    };

    /**
     * Iterate through all object values and format
     * those we recognize as a 'date' value
     */

    $scope.format_date_values = (state_obj, date_columns) => {
      if (!state_obj || !state_obj.length) return;
      if (!date_columns || !date_columns.length) return;

      // Look for each 'date' type value in all Property State values
      // and update format accordingly.
      _.forEach(date_columns, (key) => {
        if (state_obj[key]) {
          state_obj[key] = $filter('date')(state_obj[key], 'MM/dd/yyyy');
        }
      });
    };

    /**
     * Compare edits with original
     */
    $scope.diff = () => {
      if (_.isEmpty($scope.item_copy)) return {};
      // $scope.item_state, $scope.item_copy
      const ignored_root_keys = ['extra_data', 'files', 'measures', 'scenarios'];
      const result = {};
      _.forEach($scope.item_state, (value, key) => {
        if (ignored_root_keys.includes(key)) return;
        if (value === $scope.item_copy[key]) return;
        if (_.isNull($scope.item_copy[key]) && _.isString(value) && _.isEmpty(value)) return;
        if (_.isNumber($scope.item_copy[key]) && _.isString(value) && $scope.item_copy[key] === _.toNumber(value)) return;

        _.set(result, key, value);
      });
      _.forEach($scope.item_state.extra_data, (value, key) => {
        if (value === $scope.item_copy.extra_data[key]) return;
        if (_.isNull($scope.item_copy.extra_data[key]) && _.isString(value) && _.isEmpty(value)) return;
        if (_.isNumber($scope.item_copy.extra_data[key]) && _.isString(value) && $scope.item_copy.extra_data[key] === _.toNumber(value)) return;

        _.set(result, `extra_data.${key}`, value);
      });

      return result;
    };

    /**
     * Check if the edits are actually modified
     */
    $scope.modified = () => !_.isEmpty($scope.diff());

    /**
     * User clicked 'save' button
     */
    $scope.on_save = () => {
      $scope.open_match_merge_link_warning_modal($scope.save_item, 'edit');
    };

    const notify_merges_and_links = (result) => {
      const singular = $scope.inventory_type === 'properties' ? ' property' : ' tax lot';
      const plural = $scope.inventory_type === 'properties' ? ' properties' : ' tax lots';
      const merged_count = result.match_merged_count;
      const link_count = result.match_link_count;

      Notification.info({
        message: `${merged_count} total ${merged_count === 1 ? singular : plural} merged`,
        delay: 10000
      });
      Notification.info({
        message: `${link_count} cross-cycle link${link_count === 1 ? '' : 's'} established`,
        delay: 10000
      });
    };

    /**
     * save_item: saves the user's changes to the Property/TaxLot State object.
     */
    const save_item_resolve = (data) => {
      $scope.$emit('finished_saving');
      notify_merges_and_links(data);
      if (data.view_id) {
        reload_with_view_id(data.view_id);
      } else {
        // In the short term, we're just refreshing the page after a save so the table
        // shows new history.
        // TODO: Refactor so that table is dynamically updated with new information
        $state.reload();
      }
    };

    const save_item_reject = () => {
      $scope.$emit('finished_saving');
    };

    const save_item_catch = (data) => {
      $log.error(String(data));
    };

    $scope.save_item = () => {
      if ($scope.inventory_type === 'properties') {
        inventory_service.update_property($scope.inventory.view_id, $scope.diff()).then(save_item_resolve, save_item_reject).catch(save_item_catch);
      } else if ($scope.inventory_type === 'taxlots') {
        inventory_service.update_taxlot($scope.inventory.view_id, $scope.diff()).then(save_item_resolve, save_item_reject).catch(save_item_catch);
      }
    };

    /** Open a model to edit labels for the current detail item. */

    $scope.open_update_labels_modal = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/update_item_labels_modal.html`,
        controller: 'update_item_labels_modal_controller',
        resolve: {
          inventory_ids: () => [$scope.inventory.view_id],
          inventory_type: () => $scope.inventory_type,
          is_ali_root: () => $scope.menu.user.is_ali_root
        }
      });
      modalInstance.result.then(
        () => {
          label_service.get_labels($scope.inventory_type, [$scope.inventory.view_id]).then((labels) => {
            $scope.labels = _.filter(labels, (label) => !_.isEmpty(label.is_applied));
          });
        },
        () => {
          // Do nothing
        }
      );
    };
    $scope.open_ubid_admin_modal = () => {
      $uibModal.open({
        backdrop: 'static',
        templateUrl: `${urls.static_url}seed/partials/ubid_admin_modal.html`,
        controller: 'ubid_admin_modal_controller',
        resolve: {
          property_view_id: () => ($scope.inventory_type === 'properties' ? $scope.inventory.view_id : null),
          taxlot_view_id: () => ($scope.inventory_type === 'taxlots' ? $scope.inventory.view_id : null),
          inventory_payload: [
            '$state',
            '$stateParams',
            'inventory_service',
            ($state, $stateParams, inventory_service) => ($scope.inventory_type === 'properties' ? inventory_service.get_property($scope.inventory.view_id) : inventory_service.get_taxlot($scope.inventory.view_id))
          ]
        }
      });
    };

    $scope.open_analyses_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/inventory_detail_analyses_modal.html`,
        controller: 'inventory_detail_analyses_modal_controller',
        resolve: {
          inventory_ids: () => [$scope.inventory.view_id],
          current_cycle: () => $scope.cycle,
          cycles: () => cycle_service.get_cycles().then((result) => result.cycles),
          user: () => $scope.menu.user
        }
      });
    };

    $scope.unmerge = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/unmerge_modal.html`,
        controller: 'unmerge_modal_controller',
        resolve: {
          inventory_type: () => $scope.inventory_type
        }
      });

      return modalInstance.result
        .then(() => {
          if ($scope.inventory_type === 'properties') {
            return matching_service.unmergeProperties($scope.inventory.view_id);
          }
          return matching_service.unmergeTaxlots($scope.inventory.view_id);
        })
        .then((result) => {
          $state.go('inventory_detail', {
            inventory_type: $scope.inventory_type,
            view_id: result.view_id
          });
        });
    };

    $scope.open_data_upload_audit_template_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/data_upload_audit_template_modal.html`,
        controller: 'data_upload_audit_template_modal_controller',
        resolve: {
          audit_template_building_id: () => $scope.audit_template_building_id,
          organization: () => $scope.organization,
          cycle_id: () => $scope.cycle.id,
          upload_from_file: () => $scope.uploaderfunc,
          view_id: () => $stateParams.view_id
        },
        backdrop: 'static'
      });
    };

    $scope.open_data_upload_espm_modal = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/data_upload_espm_modal.html`,
        controller: 'data_upload_espm_modal_controller',
        resolve: {
          pm_property_id: () => $scope.pm_property_id,
          organization: () => $scope.organization,
          cycle_id: () => $scope.cycle.id,
          upload_from_file: () => $scope.uploaderfunc,
          view_id: () => $stateParams.view_id,
          column_mapping_profiles: [
            'column_mappings_service',
            (column_mappings_service) => column_mappings_service.get_column_mapping_profiles_for_org($scope.organization.id, []).then((response) => response.data)
          ]
        }
      });
      modalInstance.result.then(() => {});
    };

    $scope.open_export_to_audit_template_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/export_to_audit_template_modal.html`,
        controller: 'export_to_audit_template_modal_controller',
        resolve: {
          ids: () => [$stateParams.view_id],
          org_id: () => $scope.organization.id
        }
      });
    };

    $scope.export_building_sync = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/export_buildingsync_modal.html`,
        controller: 'export_buildingsync_modal_controller',
        resolve: {
          property_view_id: () => $stateParams.view_id,
          column_mapping_profiles: [
            'column_mappings_service',
            'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT',
            'COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM',
            (column_mappings_service, COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT, COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM) => {
              const filter_profile_types = [COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_DEFAULT, COLUMN_MAPPING_PROFILE_TYPE_BUILDINGSYNC_CUSTOM];
              return column_mappings_service.get_column_mapping_profiles_for_org($scope.organization.id, filter_profile_types).then((response) => response.data);
            }
          ]
        }
      });
      modalInstance.result.then(() => {});
    };

    $scope.export_building_sync_xlsx = () => {
      const filename = `buildingsync_property_${$stateParams.view_id}.xlsx`;
      // var profileId = null;
      // if ($scope.currentProfile) {
      //   profileId = $scope.currentProfile.id;
      // }

      $http
        .post(
          '/api/v3/tax_lot_properties/export/',
          {
            ids: [$stateParams.view_id],
            filename,
            profile_id: null, // TODO: reconfigure backend to handle detail settings profiles
            export_type: 'xlsx'
          },
          {
            params: {
              organization_id: $scope.organization.id,
              inventory_type: $scope.inventory_type
            },
            responseType: 'arraybuffer'
          }
        )
        .then((response) => {
          const blob_type = response.headers()['content-type'];

          const blob = new Blob([response.data], { type: blob_type });
          saveAs(blob, filename);
        });
    };

    $scope.unpair_property_from_taxlot = (property_id) => {
      pairing_service.unpair_property_from_taxlot($scope.inventory.view_id, property_id);
      $state.reload();
    };

    $scope.unpair_taxlot_from_property = (taxlot_id) => {
      pairing_service.unpair_taxlot_from_property($scope.inventory.view_id, taxlot_id);
      $state.reload();
    };

    const reload_with_view_id = (view_id) => {
      $state.go('inventory_detail', {
        inventory_type: $scope.inventory_type,
        view_id
      });
    };

    $scope.update_salesforce = () => {
      inventory_service
        .update_salesforce([$scope.inventory.view_id])
        .then((/* result */) => {
          $state.reload();
          Notification.success({ message: 'Salesforce Update Successful!', delay: 5000 });
        })
        .catch((result) => {
          Notification.error({ message: `Error updating Salesforce: ${result.data.message}`, delay: 15000, closeOnClick: true });
        });
    };

    $scope.match_merge_link_record = () => {
      if ($scope.inventory_type === 'properties') {
        match_merge_link_fn = inventory_service.property_match_merge_link
      } else if ($scope.inventory_type === 'taxlots') {
        match_merge_link_fn = inventory_service.taxlot_match_merge_link
      }

      match_merge_link_fn($scope.inventory.view_id)
      .then(result => {
        notify_merges_and_links(result);
        new_view_id = result.view_id;
        if (new_view_id) reload_with_view_id(new_view_id);
      })
      .catch(result => {
        Notification.error({
          message: result.data.message,
          delay: 10000
        });
      });
    };

    $scope.open_match_merge_link_warning_modal = (accept_action, trigger) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/record_match_merge_link_modal.html`,
        controller: 'record_match_merge_link_modal_controller',
        resolve: {
          inventory_type: () => $scope.inventory_type,
          organization_id: () => $scope.organization.id,
          headers() {
            if (trigger === 'manual') {
              return {
                properties: 'Merge and Link Matching Properties',
                taxlots: 'Merge and Link Matching Tax Lots'
              };
            }
            if (trigger === 'edit') {
              return {
                properties: 'Updating this property will trigger a matching round for this record.',
                taxlots: 'Updating this tax lot will trigger a matching round for this record.'
              };
            }
          }
        }
      });

      modalInstance.result.then(accept_action, () => {
        // Do nothing if cancelled
      });
    };

    $scope.uploader = {
      invalid_xml_extension_alert: false,
      invalid_xlsx_extension_alert: false,
      in_progress: false,
      progress: 0,
      complete: false,
      status_message: ''
    };

    $scope.uploaderfunc = (event_message, file, progress) => {
      switch (event_message) {
        case 'invalid_xml_extension':
          $scope.uploader.invalid_xml_extension_alert = true;
          break;

        case 'invalid_extension':
          $scope.uploader.invalid_xlsx_extension_alert = true;
          break;

        case 'upload_submitted':
          $scope.uploader.filename = file.filename;
          $scope.uploader.invalid_xml_extension_alert = false;
          $scope.uploader.invalid_xlsx_extension_alert = false;
          $scope.uploader.in_progress = true;
          $scope.uploader.status_message = 'uploading file';
          break;

        case 'upload_error':
          $scope.uploader.status_message = 'upload failed';
          $scope.uploader.complete = false;
          $scope.uploader.in_progress = false;
          $scope.uploader.progress = 0;
          alert(file.error);
          break;

        case 'upload_in_progress':
          $scope.uploader.in_progress = true;
          $scope.uploader.progress = (100 * progress.loaded) / progress.total;
          break;

        case 'upload_complete':
          $scope.uploader.status_message = 'upload complete';
          $scope.uploader.complete = true;
          $scope.uploader.in_progress = false;
          $scope.uploader.progress = 100;
          $state.reload();
          break;
      }

      _.defer(() => {
        $scope.$apply();
      });
    };

    // Horizontal scroll for "2 tables" that scroll together for fixed header effect.
    const table_container = $('.table-xscroll-fixed-header-container');

    table_container.scroll(() => {
      $('.table-xscroll-fixed-header-container > .table-body-x-scroll').width(table_container.width() + table_container.scrollLeft());
    });

    $scope.displayValue = (dataType, value) => {
      if (dataType === 'datetime') {
        return $filter('date')(value, 'yyyy-MM-dd h:mm a');
      }
      if (['area', 'eui', 'float', 'number'].includes(dataType)) {
        return $filter('number')(value, $scope.organization.display_decimal_places);
      }
      return value;
    };

    // evaluate all derived columns and store the results
    const evaluate_derived_columns = () => {
      const visible_columns_with_derived_columns = $scope.columns.filter((col) => col.derived_column);
      const derived_column_ids = visible_columns_with_derived_columns.map((col) => col.derived_column);
      const attached_derived_columns = derived_columns_payload.derived_columns.filter((col) => derived_column_ids.includes(col.id));
      const column_name_lookup = {};
      visible_columns_with_derived_columns.forEach((col) => {
        column_name_lookup[col.column_name] = col.name;
      });

      const all_evaluation_results = attached_derived_columns.map((col) => derived_columns_service.evaluate($scope.organization.id, col.id, $scope.cycle.id, [$scope.item_parent.id]).then((res) => ({
        derived_column_id: col.id,
        value: _.round(res.results[0].value, $scope.organization.display_decimal_places)
      })));

      $q.all(all_evaluation_results).then((results) => {
        results.forEach((result) => {
          const col_id = $scope.columns.find((col) => col.derived_column === result.derived_column_id).id;
          $scope.item_derived_values[col_id] = result.value;
        });
      });
    };

    $scope.delete_scenario = (scenario_id, scenario_name) => {
      const property_view_id = $stateParams.view_id;

      const modalOptions = {
        type: 'default',
        okButtonText: 'Yes',
        cancelButtonText: 'Cancel',
        headerText: 'Are you sure?',
        bodyText: `You're about to permanently delete scenario "${scenario_name}". Would you like to continue?`
      };
      // user confirmed, delete it
      simple_modal_service.showModal(modalOptions).then(() => {
        scenario_service
          .delete_scenario($scope.org.id, property_view_id, scenario_id)
          .then(() => {
            Notification.success(`Deleted "${scenario_name}"`);
            // location.reload();
            // Prevent page from reloading, retain user's scroll location
            let promise;
            if ($stateParams.inventory_type === 'properties') promise = inventory_service.get_property(property_view_id);
            else if ($stateParams.inventory_type === 'taxlots') promise = inventory_service.get_taxlot(property_view_id);
            promise.then((data) => {
              $scope.historical_items = data.history;
              $scope.historical_items_with_scenarios = $scope.historical_items ? $scope.historical_items.filter((item) => !_.isEmpty(item.state.scenarios)) : [];
              $scope.order_historical_items_with_scenarios();
            });
          })
          .catch((err) => {
            $log.error(err);
            Notification.error(`Error attempting to delete "${scenario_name}". Please refresh the page and try again.`);
          });
      });
    };

    $scope.getStatusOfMeasures = (scenario) => {
      const statusCount = scenario.measures.reduce((acc, measure) => {
        const status = measure.implementation_status;
        if (!acc[status]) {
          acc[status] = 0;
        }
        acc[status]++;
        return acc;
      }, {});

      return statusCount;
    };

    const setMeasureGridOptions = () => {
      if (!$scope.historical_items) {
        return;
      }

      $scope.measureGridOptionsByScenarioId = {};
      $scope.gridApiByScenarioId = {};

      const at_scenarios = $scope.historical_items.filter((item) => !_.isEmpty(item.state.scenarios)).map((item) => item.state.scenarios);
      const scenarios = [].concat(...at_scenarios);
      scenarios.forEach((scenario) => {
        const scenario_id = scenario.id;
        const measureGridOptions = {
          data: scenario.measures.map((measure) => ({
            category: measure.category,
            name: measure.display_name,
            recommended: measure.recommended,
            status: measure.implementation_status,
            category_affected: measure.category_affected,
            cost_installation: measure.cost_installation,
            cost_material: measure.cost_material,
            cost_residual_value: measure.cost_residual_value,
            cost_total_first: measure.cost_total_first,
            cost_capital_replacement: measure.cost_capital_replacement,
            description: measure.description,
            useful_life: measure.useful_life,
            id: measure.id,
            scenario_id
          })),
          columnDefs: [
            { field: 'category' },
            { field: 'name' },
            { field: 'recommended' },
            { field: 'status' },
            { field: 'category_affected' },
            { field: 'cost_installation' },
            { field: 'cost_material' },
            { field: 'cost_residual_value' },
            { field: 'cost_total_first' },
            { field: 'cost_capital_replacement' },
            { field: 'description' },
            { field: 'useful_life' },
            { field: 'id', visible: false },
            { field: 'scenario_id', visible: false }
          ],
          enableColumnMenus: false,
          enableHorizontalScrollbar: uiGridConstants.scrollbars.WHEN_NEEDED,
          enableVerticalScrollbar: scenario.measures.length <= 10 ? uiGridConstants.scrollbars.NEVER : uiGridConstants.scrollbars.WHEN_NEEDED,
          minRowsToShow: Math.min(scenario.measures.length, 10),
          rowHeight: 40,
          onRegisterApi(gridApi) {
            $scope.gridApiByScenarioId[scenario.id] = gridApi;
          }
        };
        $scope.measureGridOptionsByScenarioId[scenario.id] = measureGridOptions;
      });
    };
    $scope.resizeGridByScenarioId = (scenarioId) => {
      const gridApi = $scope.gridApiByScenarioId[scenarioId];
      setTimeout(gridApi.core.handleWindowResize, 50);
    };

    $scope.formatMeasureStatuses = (scenario) => {
      const statuses = scenario.measures.reduce((acc, measure) => {
        const status = measure.implementation_status;
        if (!acc[status]) {
          acc[status] = 0;
        }
        acc[status]++;
        return acc;
      }, {});
      return statuses;
    };

    $scope.accordionsCollapsed = true;
    $scope.collapseAccordions = (collapseAll) => {
      $scope.accordionsCollapsed = collapseAll;
      const action = collapseAll ? 'hide' : 'show';
      $('.event-collapse').collapse(action);
      $('.scenario-collapse').collapse(action);

      // Without resizing ui-grids will appear empty
      if (action === 'show') {
        const scenarios = $scope.historical_items_with_scenarios.map((item) => item.state.scenarios).flat();
        scenarios.forEach((scenario) => $scope.resizeGridByScenarioId(scenario.id));
      }
    };

    /**
     *   init: sets default state of inventory detail page,
     *   sets the field arrays for each section, performs
     *   some date string manipulation for better display rendering,
     *   and gets all the extra_data fields
     *
     */
    const init = () => {
      if ($scope.inventory_type === 'properties') {
        $scope.format_date_values($scope.item_state, inventory_service.property_state_date_columns);
      } else if ($scope.inventory_type === 'taxlots') {
        $scope.format_date_values($scope.item_state, inventory_service.taxlot_state_date_columns);
      }

      evaluate_derived_columns();
      setMeasureGridOptions();
    };

    $scope.confirm_delete = (file) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/delete_document_modal.html`,
        controller: 'delete_document_modal_controller',
        resolve: {
          view_id: () => $scope.inventory.view_id,
          file
        }
      });

      modalInstance.result.finally(() => {
        init();
      });
    };

    init();

    $scope.toggle_freeze = () => {
      const table_div = document.getElementById('pin');
      if (table_div.className === 'section_content_container table-xscroll-unfrozen') {
        table_div.className = 'section_content_container table-xscroll-frozen';
      } else {
        table_div.className = 'section_content_container table-xscroll-unfrozen';
      }
    };
  }
]);
