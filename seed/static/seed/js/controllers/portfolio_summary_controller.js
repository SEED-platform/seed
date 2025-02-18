/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.portfolio_summary', [])
  .controller('portfolio_summary_controller', [
    '$scope',
    '$state',
    '$stateParams',
    '$uibModal',
    '$window',
    'urls',
    'ah_service',
    'data_quality_service',
    'inventory_service',
    'label_service',
    'goal_service',
    'Notification',
    'cycles',
    'organization_payload',
    'access_level_tree',
    'auth_payload',
    'property_columns',
    'uiGridConstants',
    'gridUtil',
    'spinner_utility',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      $uibModal,
      $window,
      urls,
      ah_service,
      data_quality_service,
      inventory_service,
      label_service,
      goal_service,
      Notification,
      cycles,
      organization_payload,
      access_level_tree,
      auth_payload,
      property_columns,
      uiGridConstants,
      gridUtil,
      spinner_utility
    ) {
      $scope.organization = organization_payload.organization;
      $scope.viewer = $scope.menu.user.organization.user_role === 'viewer';
      $scope.write_permission = ($scope.menu.user.is_ali_root || !$scope.menu.user.is_ali_leaf) && !$scope.viewer;
      // Ii there a better way to convert string units to displayUnits?
      const area_units = $scope.organization.display_units_area.replace('**2', '²');
      const eui_units = $scope.organization.display_units_eui.replace('**2', '²');
      $scope.cycles = cycles.cycles;
      $scope.access_level_tree = access_level_tree.access_level_tree;
      $scope.level_names = access_level_tree.access_level_names;
      $scope.goal = {};
      $scope.columns = property_columns;
      $scope.cycle_columns = [];
      $scope.area_columns = [];
      $scope.eui_columns = [];
      const matching_column_names = [];
      const table_column_ids = [];
      $scope.selected_count = 0;
      $scope.selected_option = 'none';
      $scope.search_query = '';

      $scope.search_for_goals = (query) => {
        const pattern = query.split('').join('.*');
        const regex = new RegExp(pattern, 'i');
        $scope.goal_options = $scope.goals.filter((goal) => regex.test(goal.name));
      };

      const initialize_columns = () => {
        $scope.columns.forEach((col) => {
          const matching = ['pm_property_id', 'property_name'].includes(col.column_name);
          const area = col.data_type === 'area';
          const eui = col.data_type === 'eui';
          const other = ['property_name', 'property_type', 'year_built'].includes(col.column_name);

          if (matching || eui || area || other) table_column_ids.push(col.id);
          if (eui) $scope.eui_columns.push(col);
          if (area) $scope.area_columns.push(col);
          if (matching) matching_column_names.push(col.column_name);
        });
      };
      initialize_columns();

      // Can only sort based on baseline or current, not both. In the event of a conflict, use the more recent.
      let baseline_first = false;

      const load_data = (page) => {
        $scope.data_loading = true;
        const per_page = 50;
        const data = {
          goal_id: $scope.goal.id,
          page,
          per_page,
          baseline_first,
          access_level_instance_id: $scope.goal.access_level_instance,
          related_model_sort: $scope.related_model_sort
        };
        const column_filters = $scope.column_filters;
        const order_by = $scope.column_sorts;
        goal_service.load_data(data, column_filters, order_by).then((response) => {
          const data = response.data;
          $scope.inventory_pagination = data.pagination;
          $scope.property_lookup = data.property_lookup;
          $scope.data = data.properties;
          get_all_labels();
          set_grid_options();
          $scope.data_valid = Boolean(data.properties);
          $scope.data_loading = false;
        });
      };

      // optionally pass a goal name to be set as $scope.goal - used on modal close
      const get_goals = (goal_name = false) => {
        goal_service.get_goals().then((result) => {
          $scope.goals = result.goals;
          $scope.goal_options = result.goals;
          $scope.goal = goal_name ?
            $scope.goals.find((goal) => goal.name === goal_name) :
            $scope.goals[0];
          format_goal_details();
          load_summary();
          load_data(1);
        });
      };
      get_goals();

      const reset_data = () => {
        format_goal_details();
        refresh_data();
      };

      $scope.select_goal = (selected_goal) => {
        $scope.goal = selected_goal;
      };

      // If goal changes, reset grid filters and repopulate ui-grids
      $scope.$watch('goal', (cur, old) => {
        if ($scope.gridApi) $scope.reset_sorts_filters();
        $scope.data_valid = false;
        $scope.valid = true;
        if (_.isEmpty($scope.goal)) {
          $scope.valid = false;
          $scope.summary_valid = false;
        } else if (old?.id) { // prevent duplicate request on page load
          reset_data();
        }
      });

      // selected goal details
      const format_goal_details = () => {
        $scope.change_selected_level_index();
        const access_level_instance = $scope.potential_level_instances.find((level) => level.id === $scope.goal.access_level_instance).name;

        const commitment_sqft = $scope.goal.commitment_sqft?.toLocaleString() || 'n/a';
        $scope.goal_details = [
          { // column 1
            Type: capitalize($scope.goal.type),
            'Baseline Cycle': $scope.goal.baseline_cycle_name,
            'Current Cycle': $scope.goal.current_cycle_name,
            [$scope.goal.level_name]: access_level_instance,
            'Total Properties': null,
            'Portfolio Target': `${$scope.goal.target_percentage} %`
          },
          { // column 2
            'Commitment Sq. Ft': commitment_sqft,
            'Area Column': $scope.goal.area_column_name,
            'Primary EUI': $scope.goal.eui_column1_name
          }
        ];
        if ($scope.goal.eui_column2) {
          $scope.goal_details[1]['Secondary EUI'] = $scope.goal.eui_column2_name;
        }
        if ($scope.goal.eui_column3) {
          $scope.goal_details[1]['Tertiary EUI'] = $scope.goal.eui_column3_name;
        }
        if ($scope.goal.type === 'transaction') {
          $scope.goal_details[1].Transactions = $scope.goal.transactions_column_name;
        }
      };

      const capitalize = (word) => {
        if (!word) return word;
        return word.charAt(0).toUpperCase() + word.slice(1);
      };

      $scope.toggle_help = (bool) => {
        $scope.show_help = bool;
        _.delay($scope.updateHeight, 150);
      };

      const get_goal_stats = (summary) => {
        const passing_sqft = summary.current_total_sqft;
        // show help text if less than {50}% of properties are passing checks
        $scope.show_help = summary.total_passing <= summary.total_properties * 0.5;
        $scope.goal_stats = [
          { name: 'Commitment (Sq. Ft)', value: $scope.goal.commitment_sqft },
          { name: 'Shared (Sq. Ft)', value: summary.shared_sqft },
          { name: 'Passing Checks (Sq. Ft)', value: passing_sqft },
          { name: 'Passing Checks (% of committed)', value: summary.passing_committed },
          { name: 'Passing Checks (% of shared)', value: summary.passing_shared },
          { name: 'Total Passing Checks', value: summary.total_passing },
          { name: 'Total New or Acquired', value: summary.total_new_or_acquired }
        ];
      };

      // from inventory_list_controller
      $scope.columnDisplayByName = {};
      for (const i in $scope.columns) {
        $scope.columnDisplayByName[$scope.columns[i].name] = $scope.columns[i].displayName;
      }

      const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);

      $scope.change_selected_level_index = () => {
        const new_level_instance_depth = parseInt($scope.goal.level_name_index, 10) + 1;
        $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
      };

      // GOAL EDITOR MODAL
      $scope.open_goal_editor_modal = () => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/goal_editor_modal.html`,
          controller: 'goal_editor_modal_controller',
          size: 'lg',
          backdrop: 'static',
          resolve: {
            access_level_tree: () => access_level_tree,
            area_columns: () => $scope.area_columns,
            auth_payload: () => auth_payload,
            columns: () => $scope.columns,
            cycles: () => $scope.cycles,
            eui_columns: () => $scope.eui_columns,
            goal: () => $scope.goal,
            organization: () => $scope.organization,
            write_permission: () => $scope.write_permission
          }
        });

        // on modal close
        modalInstance.result.then((goal_name) => {
          get_goals(goal_name);
        });
      };

      const refresh_data = () => {
        load_summary();
        load_data(1);
      };

      const load_summary = () => {
        $scope.summary_loading = true;
        $scope.show_access_level_instances = false;
        $scope.summary_valid = false;

        goal_service.get_portfolio_summary($scope.goal.id).then((result) => {
          const summary = result.data;
          set_summary_grid_options(summary);
        }).then(() => {
          $scope.summary_loading = false;
          $scope.summary_valid = true;
        });
      };

      $scope.page_change = (page) => {
        spinner_utility.show();
        load_data(page);
      };

      // -------------- LABEL LOGIC -------------

      $scope.max_label_width = 750;
      $scope.get_label_column_width = (labels_col, key) => {
        const renderContainer = document.body.getElementsByClassName('ui-grid-render-container-body')[1];
        if (!$scope.show_full_labels[key] || !renderContainer) {
          return 31;
        }
        let maxWidth = 0;
        const col = $scope.gridApi.grid.getColumn(labels_col);
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

      // Expand or contract labels col
      $scope.show_full_labels = { baseline: false, current: false };
      $scope.toggle_labels = (labels_col, key) => {
        $scope.show_full_labels[key] = !$scope.show_full_labels[key];
        setTimeout(() => {
          $scope.gridApi.grid.getColumn(labels_col).width = $scope.get_label_column_width(labels_col, key);
          const icon = document.getElementById(`label-header-icon-${key}`);
          icon.classList.add($scope.show_full_labels[key] ? 'fa-chevron-circle-left' : 'fa-chevron-circle-right');
          icon.classList.remove($scope.show_full_labels[key] ? 'fa-chevron-circle-right' : 'fa-chevron-circle-left');
          $scope.gridApi.grid.refresh();
        }, 0);
      };

      // retrieve labels, key = 'baseline' or 'current'
      const get_labels = (key) => {
        label_service.get_property_view_labels_by_goal($scope.organization.id, $scope.goal.id, key).then((labels) => {
          if (key === 'baseline') {
            $scope.baseline_labels = labels;
            $scope.build_labels(key, $scope.baseline_labels);
          } else {
            $scope.current_labels = labels;
            $scope.build_labels(key, $scope.current_labels);
          }
        });
      };

      const get_all_labels = () => {
        get_labels('baseline');
        get_labels('current');
      };

      // Find labels that should be displayed and organize by applied inventory id
      $scope.show_labels_by_inventory_id = { baseline: {}, current: {} };
      $scope.build_labels = (key, labels) => {
        $scope.show_labels_by_inventory_id[key] = {};
        for (const n in labels) {
          const label = labels[n];
          const property_id = $scope.property_lookup[label.propertyview];
          if (!$scope.show_labels_by_inventory_id[key][property_id]) {
            $scope.show_labels_by_inventory_id[key][property_id] = [];
          }
          $scope.show_labels_by_inventory_id[key][property_id].push(label);
        }
      };

      // Builds the html to display labels associated with this row entity
      $scope.display_labels = (entity, key) => {
        const id = entity.id;
        const labels = [];
        const titles = [];
        if ($scope.show_labels_by_inventory_id[key][id]) {
          for (const i in $scope.show_labels_by_inventory_id[key][id]) {
            const label = $scope.show_labels_by_inventory_id[key][id][i];
            labels.push('<span class="', $scope.show_full_labels[key] ? 'label' : 'label-bar', ' label-', label.label, '">', $scope.show_full_labels[key] ? label.text : '', '</span>');
            titles.push(label.text);
          }
        }
        return ['<span title="', titles.join(', '), '" class="label-bars" style="overflow-x:scroll">', labels.join(''), '</span>'].join('');
      };

      // Build column defs for baseline or current labels
      const build_label_col_def = (labels_col, key) => {
        const header_cell_template = `<i ng-click="grid.appScope.toggle_labels('${labels_col}', '${key}')" class='ui-grid-cell-contents fas fa-chevron-circle-right' id='label-header-icon-${key}' style='margin:2px; float:right;'></i>`;
        const cell_template = `<div ng-click="grid.appScope.toggle_labels('${labels_col}', '${key}')" class='ui-grid-cell-contents' ng-bind-html="grid.appScope.display_labels(row.entity, '${key}')"></div>`;
        const width_fn = $scope.gridApi ? $scope.get_label_column_width(labels_col, key) : 31;

        return {
          name: labels_col,
          displayName: '',
          headerCellTemplate: header_cell_template,
          cellTemplate: cell_template,
          enableColumnMenu: false,
          enableColumnMoving: false,
          enableColumnResizing: false,
          enableFiltering: false,
          enableHiding: false,
          enableSorting: false,
          exporterSuppressExport: true,
          // pinnedLeft: true,
          visible: true,
          width: width_fn,
          maxWidth: $scope.max_label_width
        };
      };

      // ------------ DATA TABLE LOGIC ---------

      const apply_defaults = (cols, ...defaults) => {
        _.map(cols, (col) => _.defaults(col, ...defaults));
      };

      const property_column_names = [...new Set(
        [
          'pm_property_id',
          'property_name',
          'property_type',
          'year_built'
        ]
      )];

      $scope.question_options = [
        { id: 0, value: null },
        { id: 1, value: 'Is this a new construction or acquisition?' },
        { id: 2, value: 'Do you have data to report?' },
        { id: 3, value: 'Is this value correct?' },
        { id: 4, value: 'Are these values correct?' },
        { id: 5, value: 'Other or multiple flags; explain in Additional Notes field' }
      ];
      // handle cycle specific columns
      const selected_columns = () => {
        let cols = property_column_names.map((name) => $scope.columns.find((col) => col.column_name === name));
        // pin pm_property id and property name
        cols[0].pinnedLeft = true;
        cols[1].pinnedLeft = true;
        const default_baseline = { headerCellClass: 'portfolio-summary-baseline-header', cellClass: 'portfolio-summary-baseline-cell' };
        const default_current = { headerCellClass: 'portfolio-summary-current-header', cellClass: 'portfolio-summary-current-cell' };
        const default_styles = { headerCellFilter: 'translate', minWidth: 75, width: 150 };
        const default_no_edit = { enableCellEdit: false };

        const { baseline_cols, current_cols, summary_cols } = $scope.goal.type === 'transaction' ?
          transaction_cols() :
          standard_cols();

        const goal_note_cols = [
          {
            field: 'goal_note.question',
            displayName: 'Question',
            enableFiltering: false,
            enableSorting: true,
            editableCellTemplate: 'ui-grid/dropdownEditor',
            editDropdownOptionsArray: $scope.question_options,
            editDropdownIdLabel: 'value',
            enableCellEdit: $scope.write_permission,
            cellClass: () => $scope.write_permission && 'cell-edit',
            // if user has write permission show a dropdown indicator
            width: 350,
            cellTemplate: `
              <div class='ui-grid-cell-contents'>
                <span ng-class="grid.appScope.write_permission && 'cell-dropdown-indicator'">
                  <span>{{row.entity.goal_note.question}}</span>
                  <i ng-if='grid.appScope.write_permission' class='fa-solid fa-chevron-down' ></i>
                </span>
              <div>
            `
          },
          {
            field: 'goal_note.resolution',
            displayName: 'Resolution',
            enableFiltering: false,
            enableSorting: true,
            enableCellEdit: !$scope.viewer,
            cellClass: !$scope.viewer && 'cell-edit',
            width: 300
          },
          {
            field: 'historical_note.text',
            displayName: 'Historical Notes',
            enableFiltering: false,
            enableSorting: true,
            enableCellEdit: !$scope.viewer,
            cellClass: !$scope.viewer && 'cell-edit',
            width: 300
          },
          {
            field: 'goal_note.passed_checks',
            displayName: 'Passed Checks',
            enableFiltering: false,
            enableSorting: true,
            editableCellTemplate: 'ui-grid/dropdownEditor',
            editDropdownOptionsArray: [{ id: 1, value: true }, { id: 2, value: false }],
            editDropdownIdLabel: 'value',
            enableCellEdit: $scope.write_permission,
            cellClass: () => $scope.write_permission && 'cell-edit',
            // if user has write permission show a dropdown indicator
            cellTemplate: `
              <div class='ui-grid-cell-contents' ng-class="row.entity.goal_note.passed_checks ? 'cell-pass' : 'cell-fail'">
                <span ng-class="grid.appScope.write_permission && 'cell-dropdown-indicator'">{{row.entity.goal_note.passed_checks}}
                  <i ng-if='grid.appScope.write_permission' class='fa-solid fa-chevron-down' ></i>
                </span>
              <div>
            `
          },
          {
            field: 'goal_note.new_or_acquired',
            displayName: 'New Build or Acquired',
            enableFiltering: false,
            enableSorting: true,
            editableCellTemplate: 'ui-grid/dropdownEditor',
            editDropdownOptionsArray: [{ id: 1, value: true }, { id: 2, value: false }],
            editDropdownIdLabel: 'value',
            enableCellEdit: $scope.write_permission,
            cellClass: () => $scope.write_permission && 'cell-edit',
            // if user has write permission show a dropdown indicator
            cellTemplate: `
              <div class='ui-grid-cell-contents' ng-class="row.entity.goal_note.new_or_acquired && 'cell-fail'">
                <span ng-class="grid.appScope.write_permission && 'cell-dropdown-indicator'">{{row.entity.goal_note.new_or_acquired}}
                  <i ng-if='grid.appScope.write_permission' class='fa-solid fa-chevron-down' ></i>
                </span>
              <div>
            `
          }

        ];

        apply_defaults(baseline_cols, default_baseline);
        apply_defaults(current_cols, default_current);
        cols = [...cols, ...baseline_cols, ...current_cols, ...summary_cols];
        apply_defaults(cols, default_no_edit);
        cols = [...cols, ...goal_note_cols];

        // Apply filters
        // from inventory_list_controller
        _.map(cols, (col) => {
          const options = {};
          // not an ideal solution. How is this done on the inventory list
          if (col.column_name === 'pm_property_id') {
            col.type = 'number';
          }
          if (col.data_type === 'datetime') {
            options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
            options.filter = inventory_service.dateFilter();
          } else if (['area', 'eui', 'float', 'number'].includes(col.data_type)) {
            options.cellFilter = `number: ${$scope.organization.display_decimal_places}`;
            options.filter = inventory_service.combinedFilter();
          } else {
            options.filter = inventory_service.combinedFilter();
          }
          return _.defaults(col, options, default_styles);
        });

        apply_cycle_sorts_and_filters(cols);
        add_access_level_names(cols);
        return cols;
      };

      const standard_cols = () => {
        const baseline_cols = [
          { field: 'baseline_cycle', displayName: 'Cycle' },
          { field: 'baseline_sqft', displayName: `Area (${area_units})`, cellFilter: 'number' },
          { field: 'baseline_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number' },
          // ktbu acts as a derived column. Disable sorting filtering
          {
            field: 'baseline_kbtu',
            displayName: 'kBTU',
            cellFilter: 'number',
            enableFiltering: false,
            enableSorting: false,
            headerCellClass: 'derived-column-display-name portfolio-summary-baseline-header'
          },
          build_label_col_def('baseline-labels', 'baseline')
        ];
        const current_cols = [
          { field: 'current_cycle', displayName: 'Cycle' },
          { field: 'current_sqft', displayName: `Area (${area_units})`, cellFilter: 'number' },
          { field: 'current_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number' },
          {
            field: 'current_kbtu',
            displayName: 'kBTU',
            cellFilter: 'number',
            enableFiltering: false,
            enableSorting: false,
            headerCellClass: 'derived-column-display-name portfolio-summary-current-header'
          },
          build_label_col_def('current-labels', 'current')
        ];
        const summary_cols = [
          {
            field: 'sqft_change', displayName: 'Sq Ft % Change', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          },
          {
            field: 'eui_change', displayName: 'EUI % Improvement', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          }
        ];

        return { baseline_cols, current_cols, summary_cols };
      };

      const transaction_cols = () => {
        const baseline_cols = [
          { field: 'baseline_cycle', displayName: 'Cycle' },
          { field: 'baseline_sqft', displayName: `Area (${area_units})`, cellFilter: 'number' },
          // ktbu and eui(t) acts as a derived column. Disable sorting filtering
          {
            field: 'baseline_kbtu',
            displayName: 'kBTU',
            cellFilter: 'number',
            enableFiltering: false,
            enableSorting: false,
            headerCellClass: 'derived-column-display-name portfolio-summary-baseline-header'
          },
          { field: 'baseline_transactions', displayName: 'Transactions (kBtu/year)', cellFilter: 'number' },
          { field: 'baseline_eui', displayName: `EUI(s) (${eui_units})`, cellFilter: 'number' },
          {
            field: 'baseline_eui_t',
            displayName: 'EUI(t) (kBtu/year)',
            cellFilter: 'number',
            enableFiltering: false,
            enableSorting: false,
            headerCellClass: 'derived-column-display-name portfolio-summary-baseline-header'
          },
          build_label_col_def('baseline-labels', 'baseline')
        ];
        const current_cols = [
          { field: 'current_cycle', displayName: 'Cycle' },
          { field: 'current_sqft', displayName: `Area (${area_units})`, cellFilter: 'number' },
          {
            field: 'current_kbtu',
            displayName: 'kBTU',
            cellFilter: 'number',
            enableFiltering: false,
            enableSorting: false,
            headerCellClass: 'derived-column-display-name portfolio-summary-current-header'
          },
          { field: 'current_transactions', displayName: 'Transactions (kBtu/year)', cellFilter: 'number' },
          { field: 'current_eui', displayName: `EUI(s) (${eui_units})`, cellFilter: 'number' },
          {
            field: 'current_eui_t',
            displayName: 'EUI(t) (kBtu/year)',
            cellFilter: 'number',
            enableFiltering: false,
            enableSorting: false,
            headerCellClass: 'derived-column-display-name portfolio-summary-current-header'
          },
          build_label_col_def('current-labels', 'current')
        ];
        const summary_cols = [
          {
            field: 'sqft_change', displayName: 'Sq Ft % Change', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          },
          {
            field: 'transactions_change', displayName: 'Transactions % Change', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          },
          {
            field: 'eui_change', displayName: 'EUI(s) % Improvement', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          },
          {
            field: 'eui_t_change', displayName: 'EUI(t) % Change', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          }
        ];

        return { baseline_cols, current_cols, summary_cols };
      };

      const apply_cycle_sorts_and_filters = (columns) => {
        // Cycle specific columns filters and sorts must be set manually
        const cycle_columns = [
          'baseline_cycle',
          'baseline_sqft',
          'baseline_eui',
          'baseline_kbtu',
          'baseline_transactions',
          'baseline_eui_t',
          'current_cycle',
          'current_sqft',
          'current_eui',
          'current_kbtu',
          'current_transactions',
          'current_eui_t'
        ];

        for (const column of columns) {
          if (cycle_columns.includes(column.field)) {
            const cycle_column = $scope.cycle_columns.find((col) => col.name === column.field);
            column.sort = cycle_column ? cycle_column.sort : {};
            column.filter.term = cycle_column ? cycle_column.filters[0].term : null;
          }
        }
      };

      const add_access_level_names = (cols) => {
        $scope.organization.access_level_names.slice(1).reverse().forEach((level) => {
          cols.unshift({
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
            visible: false,
            width: 100,
            cellClass: 'ali-cell',
            headerCellClass: 'ali-header'
          });
        });
      };

      $scope.updateHeight = () => {
        let height = 0;
        for (const selector of ['.header', '.page_header_container', '.section_nav_container', '.goals-header-text', '.goal-actions-wrapper', '.goal-details-container', '#portfolio-summary-selection-wrapper', '.portfolio-summary-item-count']) {
          const [element] = angular.element(selector);
          height += element?.offsetHeight ?? 0;
        }
        angular.element('#portfolioSummary-gridOptions-wrapper').css('height', `calc(100vh - ${height}px)`);
        $scope.summaryGridApi.core.handleWindowResize();
        $scope.gridApi.core.handleWindowResize();
        $scope.gridApi.grid.refresh();
      };

      $scope.toggle_show_access_level_instances = () => {
        $scope.show_access_level_instances = !$scope.show_access_level_instances;
        $scope.gridOptions.columnDefs.forEach((col) => {
          if (col.group === 'access_level_instance') {
            col.visible = $scope.show_access_level_instances;
          }
        });
        $scope.gridApi.core.refresh();
      };

      const format_cycle_columns = (columns) => {
        /* filtering is based on existing db columns.
        ** The PortfolioSummary uses cycle specific columns that do not exist elsewhere ('baseline_eui', 'current_sqft')
        ** To sort on these columns, override the column name to the canonical column, and set the cycle filter order
        ** ex: if sort = {name: 'baseline_sqft'}, set {name: 'gross_floor_area_##'} and filter for baseline properties first.

        ** NOTE:
        ** cant filter on cycle - cycle is not a column
        ** cant filter on kbtu, sqft_change, eui_change - not real columns. calc'ed from eui and sqft. (similar to derived columns)
        */
        const eui_column = $scope.columns.find((col) => col.id === $scope.goal.eui_column1);
        const area_column = $scope.columns.find((col) => col.id === $scope.goal.area_column);

        const cycle_column_lookup = {
          baseline_eui: eui_column.name,
          baseline_sqft: area_column.name,
          current_eui: eui_column.name,
          current_sqft: area_column.name
        };

        if ($scope.goal.transactions_column) {
          const transactions_column = $scope.columns.find((col) => col.id === $scope.goal.transactions_column);
          cycle_column_lookup.baseline_transactions = transactions_column.name;
          cycle_column_lookup.current_transactions = transactions_column.name;
        }

        $scope.cycle_columns = [];

        for (const column of columns) {
          if (cycle_column_lookup[column.name]) {
            $scope.cycle_columns.push({ ...column });
            column.name = cycle_column_lookup[column.name];
          }
        }

        return columns;
      };

      const remove_conflict_columns = (grid_columns) => {
        // Properties are returned from 2 different get requests. One for the current, one for the baseline
        // The second filter is solely based on the property ids from the first
        // Filtering on the first and second will result in unrepresentative data
        // Remove the conflict to allow sorting/filtering on either baseline or current.

        const column_names = grid_columns.map((c) => c.name);
        const includes_baseline = column_names.some((name) => name.includes('baseline'));
        const includes_current = column_names.some((name) => name.includes('current'));
        const conflict = includes_baseline && includes_current;

        if (conflict) {
          baseline_first = !baseline_first;
          const excluded_name = baseline_first ? 'current' : 'baseline';
          grid_columns = grid_columns.filter((column) => !column.name.includes(excluded_name));
        } else if (includes_baseline) {
          baseline_first = true;
        } else if (includes_current) {
          baseline_first = false;
        }
        return grid_columns;
      };

      // from inventory_list_controller
      const updateColumnFilterSort = () => {
        let grid_columns = _.filter($scope.gridApi.saveState.save().columns, (col) => _.keys(col.sort).filter((key) => key !== 'ignoreSort').length + (_.get(col, 'filters[0].term', '') || '').length > 0);
        // check filter/sort columns. Cannot filter on both baseline and current. choose the more recent filter/sort
        grid_columns = remove_conflict_columns(grid_columns);
        // convert cycle columns to canonical columns
        const formatted_columns = format_cycle_columns(grid_columns);

        $scope.column_filters = [];
        // parse the filters and sorts
        for (const column of formatted_columns) {
          // format column if cycle specific
          let { name } = column;
          const { filters, sort } = column;
          // remove the column id at the end of the name
          const column_name = name.split('_').slice(0, -1).join('_');

          for (const filter of filters) {
            if (_.isEmpty(filter)) {
              // eslint-disable-next-line no-continue
              continue;
            }

            // a filter can contain many comma-separated filters
            const subFilters = _.map(_.split(filter.term, ','), _.trim);
            for (const subFilter of subFilters) {
              if (subFilter) {
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

          $scope.related_model_sort = false;
          if (sort.direction) {
            // remove the column id at the end of the name
            let column_name;
            $scope.related_model_sort = ['historical_note.', 'goal_note.'].some((value) => name.includes(value));
            if ($scope.related_model_sort) {
              name = `property__${name.replace('.', '__')}`;
              column_name = name;
            } else {
              column_name = name.split('_').slice(0, -1).join('_');
            }
            const display = [$scope.columnDisplayByName[name], sort.direction].join(' ');
            $scope.column_sorts = [{
              name,
              column_name,
              direction: sort.direction,
              display,
              priority: sort.priority
            }];
          }
        }
      };

      // from inventory_list_controller
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

      const set_grid_options = () => {
        $scope.show_full_labels = { baseline: false, current: false };
        $scope.selected_ids = [];
        spinner_utility.hide();
        $scope.gridOptions = {
          data: 'data',
          columnDefs: selected_columns(),
          enableFiltering: true,
          enableHorizontalScrollbar: uiGridConstants.scrollbars.WHEN_NEEDED,
          cellWidth: 200,
          enableGridMenu: true,
          exporterMenuCsv: false,
          exporterMenuExcel: false,
          exporterMenuPdf: false,
          gridMenuShowHideColumns: false,
          gridMenuCustomItems: [{
            title: 'Export Page to CSV',
            action: () => $scope.gridApi.exporter.csvExport('all', 'all')
          }],
          onRegisterApi: (gridApi) => {
            $scope.gridApi = gridApi;

            _.delay($scope.updateHeight, 150);

            const debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
            angular.element($window).on('resize', debouncedHeightUpdate);
            $scope.$on('$destroy', () => {
              angular.element($window).off('resize', debouncedHeightUpdate);
            });

            gridApi.core.on.sortChanged($scope, () => {
              spinner_utility.show();
              _.debounce(() => {
                updateColumnFilterSort();
                load_data(1);
              }, 500)();
            });

            gridApi.core.on.filterChanged($scope, _.debounce(() => {
              spinner_utility.show();
              updateColumnFilterSort();
              load_data(1);
            }, 2000));

            const selectionChanged = () => {
              $scope.selected_ids = gridApi.selection.getSelectedRows().map((row) => row.current_view_id);
              $scope.selected_count = $scope.selected_ids.length;
            };
            gridApi.selection.on.rowSelectionChanged($scope, selectionChanged);
            gridApi.selection.on.rowSelectionChangedBatch($scope, selectionChanged);

            gridApi.edit.on.afterCellEdit($scope, (rowEntity, colDef, newValue) => {
              const [model, field] = colDef.field.split('.');

              if (model === 'historical_note') {
                goal_service.update_historical_note(rowEntity.id, rowEntity.historical_note.id, { [field]: newValue });
              } else if (model === 'goal_note') {
                goal_service.update_goal_note(rowEntity.id, rowEntity.goal_note.id, { [field]: newValue });
              }
              if (['passed_checks', 'new_or_acquired'].includes(field)) {
                // load_stats
                load_summary();
              }
            });
          }
        };
      };

      $scope.reset_sorts_filters = () => {
        $scope.reset_sorts();
        $scope.reset_filters();
      };
      $scope.reset_sorts = () => {
        $scope.column_sorts = [];
        $scope.gridApi.core.refresh();
      };
      $scope.reset_filters = () => {
        $scope.column_filters = [];
        $scope.gridApi.grid.clearAllFilters();
      };

      $scope.select_all = () => {
        // select all rows to visibly support everything has been selected
        $scope.gridApi.selection.selectAllRows();
        $scope.selected_count = $scope.inventory_pagination.total;
        goal_service.get_goal($scope.goal.id).then((response) => {
          const goal = response.data.goal;
          if (goal) {
            $scope.selected_ids = goal.current_cycle_property_view_ids;
          }
        });
      };

      $scope.select_none = () => {
        $scope.gridApi.selection.clearSelectedRows();
        $scope.selected_count = 0;
      };

      /**
      Opens the update building labels modal.
      All further actions for labels happen with that modal and its related controller,
      including creating a new label or applying to/removing from a building.
      When the modal is closed, and refresh labels.
      */
      $scope.open_update_labels_modal = () => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/update_item_labels_modal.html`,
          controller: 'update_item_labels_modal_controller',
          resolve: {
            inventory_ids: () => $scope.selected_ids,
            inventory_type: () => 'properties',
            is_ali_root: () => $scope.menu.user.is_ali_root
          }
        });
        modalInstance.result.then(() => {
          // dialog was closed with 'Done' button.
          $scope.selected_option = 'none';
          $scope.selected_count = 0;
          $scope.gridApi.selection.clearSelectedRows();
          load_data();
        });
      };

      /**
       Opens a modal to batch edit goal notes
       */
      $scope.open_bulk_edit_goalnotes_modal = () => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/bulk_edit_goalnotes_modal.html`,
          controller: 'bulk_edit_goalnotes_modal_controller',
          resolve: {
            property_view_ids: () => $scope.selected_ids,
            goal: () => $scope.goal,
            question_options: () => $scope.question_options,
            write_permission: () => $scope.write_permission
          }
        });
        modalInstance.result.then(() => {
          // dialog was closed with 'Done' button.
          $scope.selected_option = 'none';
          $scope.selected_count = 0;
          $scope.gridApi.selection.clearSelectedRows();
          load_summary();
          load_data();
        });
      };

      // -------- SUMMARY LOGIC ------------

      const summary_selected_columns = () => {
        const default_baseline = { headerCellClass: 'portfolio-summary-baseline-header', cellClass: 'portfolio-summary-baseline-cell' };
        const default_current = { headerCellClass: 'portfolio-summary-current-header', cellClass: 'portfolio-summary-current-cell' };
        const default_styles = { headerCellFilter: 'translate' };

        const { baseline_cols, current_cols, calc_cols } = $scope.goal.type === 'transaction' ? summary_transaction_cols() : summary_standard_cols();

        apply_defaults(baseline_cols, default_baseline, default_styles);
        apply_defaults(current_cols, default_current, default_styles);
        apply_defaults(calc_cols);

        return [...baseline_cols, ...current_cols, ...calc_cols].map((col) => ({
          ...col,
          minWidth: 50
        }));
      };

      const summary_standard_cols = () => {
        const baseline_cols = [
          { field: 'baseline_cycle_name', displayName: 'Cycle' },
          { field: 'baseline_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number' },
          { field: 'baseline_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number' },
          { field: 'baseline_weighted_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number' }
        ];
        const current_cols = [
          { field: 'current_cycle_name', displayName: 'Cycle' },
          { field: 'current_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number' },
          { field: 'current_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number' },
          { field: 'current_weighted_eui', displayName: `EUI (${eui_units})`, cellFilter: 'number' }
        ];
        const calc_cols = [
          { field: 'sqft_change', displayName: 'Area % Change' },
          {
            field: 'eui_change',
            displayName: 'EUI % Improvement',
            cellClass: (grid, row) => (row.entity.eui_change >= $scope.goal.target_percentage ? 'above-target' : 'below-target')
          }
        ];
        return { baseline_cols, current_cols, calc_cols };
      };

      const summary_transaction_cols = () => {
        const baseline_cols = [
          { field: 'baseline_cycle_name', displayName: 'Cycle' },
          { field: 'baseline_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number' },
          { field: 'baseline_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number' },
          { field: 'baseline_total_transactions', displayName: 'Total Transactions', cellFilter: 'number' },
          { field: 'baseline_weighted_eui', displayName: `EUI (s) (${eui_units})`, cellFilter: 'number' },
          { field: 'baseline_weighted_eui_t', displayName: 'EUI (t) (kBtu/year)', cellFilter: 'number' }

        ];
        const current_cols = [
          { field: 'current_cycle_name', displayName: 'Cycle' },
          { field: 'current_total_sqft', displayName: `Total Area (${area_units})`, cellFilter: 'number' },
          { field: 'current_total_kbtu', displayName: 'Total kBTU', cellFilter: 'number' },
          { field: 'current_total_transactions', displayName: 'Total Transactions', cellFilter: 'number' },
          { field: 'current_weighted_eui', displayName: `EUI (s) (${eui_units})`, cellFilter: 'number' },
          { field: 'current_weighted_eui_t', displayName: 'EUI (t) (kBtu/year)', cellFilter: 'number' }
        ];
        const calc_cols = [
          { field: 'sqft_change', displayName: 'Area % Change' },
          { field: 'transactions_change', displayName: 'Transactions % Change' },
          {
            field: 'eui_change',
            displayName: 'EUI (s) % Improvement',
            cellClass: (grid, row) => (row.entity.eui_change >= $scope.goal.target_percentage ? 'above-target' : 'below-target')
          },
          {
            field: 'eui_t_change',
            displayName: 'EUI (t) % Improvement',
            cellFilter: 'number'
          }
        ];
        return { baseline_cols, current_cols, calc_cols };
      };

      const set_summary_grid_options = (summary) => {
        $scope.goal_details[0]['Total Properties'] = summary.total_properties.toLocaleString();
        get_goal_stats(summary);
        $scope.summary_data = [summary];
        $scope.summaryGridOptions = {
          data: 'summary_data',
          columnDefs: summary_selected_columns(),
          enableHorizontalScrollbar: uiGridConstants.scrollbars.WHEN_NEEDED,
          enableVerticalScrollbar: uiGridConstants.scrollbars.NEVER,
          enableSorting: false,
          minRowsToShow: 1,
          onRegisterApi: (gridApi) => {
            $scope.summaryGridApi = gridApi;
          }
        };
      };

      // --- DATA QUALITY ---
      $scope.run_data_quality_check = () => {
        spinner_utility.show();
        data_quality_service.start_data_quality_checks([], [], $scope.goal.id)
          .then((response) => {
            data_quality_service.data_quality_checks_status(response.progress_key)
              .then((result) => {
                data_quality_service.get_data_quality_results($scope.organization.id, result.unique_id)
                  .then((dq_result) => {
                    $uibModal.open({
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
                    spinner_utility.hide();
                    load_summary();
                    load_data();
                  });
              });
          })
          .catch(() => {
            spinner_utility.hide();
            Notification.error('Unexpected Error');
          });
      };
    }]);
