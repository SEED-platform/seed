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
    'data_report_service',
    'inventory_service',
    'label_service',
    'goal_service',
    'goal_standard_service',
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
      data_report_service,
      inventory_service,
      label_service,
      goal_service,
      goal_standard_service,
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
      $scope.goal = {}; // rp
      $scope.data_report = {}
      $scope.columns = property_columns;
      $scope.cycle_columns = [];
      $scope.area_columns = [];
      $scope.eui_columns = [];
      const matching_column_names = [];
      const table_column_ids = [];
      $scope.selected_count = 0;
      $scope.selected_option = 'none';
      $scope.gridOptionsByGoal = {}
      $scope.gridApiByGoal = {}
      $scope.data_valid_by_goal = {} 
      $scope.data_loading_by_goal = {} 
      $scope.data_by_goal = {}

      console.log(goal_standard_service.test())


      const initialize_columns = () => {
        $scope.columns.forEach((col) => {
          const default_display = col.column_name === $scope.organization.property_display_field;
          const matching = col.is_matching_criteria;
          const area = col.data_type === 'area';
          const eui = col.data_type === 'eui';
          const other = ['property_name', 'property_type', 'year_built'].includes(col.column_name);

          if (default_display || matching || eui || area || other) table_column_ids.push(col.id);
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
        for (const goal of $scope.data_report.goals) {
          const goal_data = {
            goal_id: goal.id,
            data_report_id: $scope.data_report.id,
            page,
            per_page,
            baseline_first,
            access_level_instance_id: $scope.data_report.access_level_instance,
            related_model_sort: $scope.related_model_sort
          };
          const column_filters = $scope.column_filters;
          const order_by = $scope.column_sorts;
          goal_service.load_data(goal_data, column_filters, order_by).then((response) => {
            const data = response.data;
            $scope.inventory_pagination = data.pagination;
            $scope.property_lookup = data.property_lookup;
            $scope.data_by_goal[goal.id] = data.properties;
            get_all_labels();
            set_grid_options(goal.id);
            $scope.data_valid_by_goal[goal.id] = Boolean(data.properties);
            $scope.data_loading_by_goal[goal.id] = false;
            console.log(data_valid_by_goal)
            console.log(data_loading_by_goal)

          });
        }
      };

      // optionally pass a data_report name to be set as $scope.data_report - used on modal close
      const get_data_reports = (data_report_name = false) => {
        data_report_service.get_data_reports().then((result) => {
          $scope.data_reports = result.data_reports;
          $scope.data_report = data_report_name ?
            $scope.data_reports.find((data_report) => data_report.name === data_report_name) :
            $scope.data_reports[0];
          $scope.goals = $scope.data_report.goals
          $scope.goal0 = $scope.goals[0] // RP TEMP
          refresh_data();
        });
      };
      get_data_reports();

      const refresh_data = () => {
        $scope.valid = true;
        format_data_report_details();
        load_summary();
        load_data(1);
      };

      // If data_report changes, reset grid filters and repopulate ui-grids
      $scope.$watch('data_report', (cur, old) => {
        if ($scope.gridApiByGoal) $scope.reset_sorts_filters();
        $scope.data_valid = false;
        if (_.isEmpty($scope.data_report)) {
          $scope.valid = false;
          $scope.summary_valid = false;
        } else if (old.id) { // prevent duplicate request on page load
          refresh_data();
        }
      });

      // selected goal details
      const format_data_report_details = () => {
        $scope.change_selected_level_index();
        const ali = $scope.potential_level_instances.find((level) => level.id === $scope.data_report.access_level_instance).name;
        if ($scope.data_report.type === "standard") {
          $scope.data_report_details = goal_standard_service.data_report_details($scope.data_report, $scope.goal0, ali)
        }
      };

      $scope.toggle_help = () => {
        $scope.show_help = !$scope.show_help;
        _.delay(() => $scope.updateHeight($scope.data_report.goals[0]), 150);
      };

      const get_data_report_stats = (summary) => {
        $scope.show_help = summary.total_passing <= summary.total_properties * 0.5;

        if ($scope.data_report.type === "standard") {
          $scope.data_report_stats = goal_standard_service.data_report_stats(summary, $scope.data_report)
        }
      };

      // from inventory_list_controller
      $scope.columnDisplayByName = {};
      for (const i in $scope.columns) {
        $scope.columnDisplayByName[$scope.columns[i].name] = $scope.columns[i].displayName;
      }

      const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);

      $scope.change_selected_level_index = () => {
        const new_level_instance_depth = parseInt($scope.data_report.level_name_index, 10) + 1;
        $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
      };

      // DATA REPORT EDITOR MODAL
      $scope.open_data_report_editor_modal = () => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/data_report_editor_modal.html`,
          controller: 'data_report_editor_modal_controller',
          size: 'lg',
          backdrop: 'static',
          resolve: {
            access_level_tree: () => access_level_tree,
            area_columns: () => $scope.area_columns,
            auth_payload: () => auth_payload,
            data_report: () => $scope.data_report,
            cycles: () => $scope.cycles,
            eui_columns: () => $scope.eui_columns,
            // goal: () => $scope.goal, // rp - necessary?
            organization: () => $scope.organization,
            write_permission: () => $scope.write_permission
          }
        });

        // on modal close
        modalInstance.result.then((data_report) => {
          get_data_reports(data_report);
        });
      };

      const load_summary = () => {
        $scope.summary_loading = true;
        $scope.show_access_level_instances = true;
        $scope.summary_valid = false;

        data_report_service.get_portfolio_summary($scope.data_report.id).then((result) => {
          // summary is a dict with summaries for each of the goals, keyed on goal id.
          let summary = result.data
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
        const col = $scope.gridApiByGoal[$scope.goal0.id].grid.getColumn(labels_col); // RP - tricky
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
          for (const goal of $scope.data_report.goals) {
            $scope.gridApiByGoal[goal.id].grid.getColumn(labels_col).width = $scope.get_label_column_width(labels_col, key, goal.id);
            const icon = document.getElementById(`label-header-icon-${key}`);
            icon.classList.add($scope.show_full_labels[key] ? 'fa-chevron-circle-left' : 'fa-chevron-circle-right');
            icon.classList.remove($scope.show_full_labels[key] ? 'fa-chevron-circle-right' : 'fa-chevron-circle-left');
            $scope.gridApiByGoal[goal.id].grid.refresh();
          }
        }, 0);
      };

      // retrieve labels, key = 'baseline' or 'current'
      const get_labels = (key) => {
        label_service.get_property_view_labels_by_goal($scope.organization.id, $scope.goal0.id, key).then((labels) => {
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
      const build_label_col_def = (labels_col, key, goal) => {
        const header_cell_template = `<i ng-click="grid.appScope.toggle_labels('${labels_col}', '${key}')" class='ui-grid-cell-contents fas fa-chevron-circle-right' id='label-header-icon-${key}' style='margin:2px; float:right;'></i>`;
        const cell_template = `<div ng-click="grid.appScope.toggle_labels('${labels_col}', '${key}')" class='ui-grid-cell-contents' ng-bind-html="grid.appScope.display_labels(row.entity, '${key}')"></div>`;

        const width_fn = $scope.gridApiByGoal[goal] ? $scope.get_label_column_width(labels_col, key) : 31;
        

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
          $scope.organization.property_display_field,
          ...matching_column_names,
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
      const selected_columns = (goal) => {
        let cols = property_column_names.map((name) => $scope.columns.find((col) => col.column_name === name));
        const default_baseline = { headerCellClass: 'portfolio-summary-baseline-header', cellClass: 'portfolio-summary-baseline-cell' };
        const default_current = { headerCellClass: 'portfolio-summary-current-header', cellClass: 'portfolio-summary-current-cell' };
        const default_styles = { headerCellFilter: 'translate', minWidth: 75, width: 150 };
        const default_no_edit = { enableCellEdit: false };

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
          build_label_col_def('baseline-labels', 'baseline', goal)
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
          build_label_col_def('current-labels', 'current', goal)
        ];
        const summary_cols = [
          {
            field: 'sqft_change', displayName: 'Sq Ft % Change', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          },
          {
            field: 'eui_change', displayName: 'EUI % Improvement', enableFiltering: false, enableSorting: false, headerCellClass: 'derived-column-display-name'
          }
        ];

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
          if (col.pinnedLeft) {
            col.pinnedLeft = false;
          }
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

      const apply_cycle_sorts_and_filters = (columns) => {
        // Cycle specific columns filters and sorts must be set manually
        const cycle_columns = ['baseline_cycle', 'baseline_sqft', 'baseline_eui', 'baseline_kbtu', 'current_cycle', 'current_sqft', 'current_eui', 'current_kbtu', 'sqft_change', 'eui_change'];

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
            visible: true,
            width: 100,
            cellClass: 'ali-cell',
            headerCellClass: 'ali-header'
          });
        });
      };

      $scope.updateHeight = (goal_id) => {
        let height = 0;
        for (const selector of ['.header', '.page_header_container', '.section_nav_container', '.goals-header-text', '.goal-actions-wrapper', '.goal-details-container', '#goal-summary-goal-container', '.goal-data-actions-header']) {
          const [element] = angular.element(selector);
          height += element?.offsetHeight ?? 0;
        }
        angular.element('#goal-data-gridOptions-wrapper').css('height', `calc(100vh - ${height}px)`);

        $scope.summaryGridApiByGoal[goal_id].core.handleWindowResize();
        $scope.gridApiByGoal[goal_id].core.handleWindowResize();
        $scope.gridApiByGoal[goal_id].grid.refresh();

      };

      $scope.toggle_show_access_level_instances = () => {
        $scope.show_access_level_instances = !$scope.show_access_level_instances;
        $scope.gridOptions.columnDefs.forEach((col) => {
          if (col.group === 'access_level_instance') {
            col.visible = $scope.show_access_level_instances;
          }
        });
        for (const goal in $scope.data_report.goals) {
          $scope.gridApiByGoal[goal].core.refresh();
        }
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
        const eui_column = $scope.columns.find((col) => col.id === $scope.goal0.eui_column1);
        const area_column = $scope.columns.find((col) => col.id === $scope.goal0.area_column);

        const cycle_column_lookup = {
          baseline_eui: eui_column.name,
          baseline_sqft: area_column.name,
          current_eui: eui_column.name,
          current_sqft: area_column.name
        };
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
      const updateColumnFilterSort = (goal_id) => {
        let grid_columns = _.filter($scope.gridApiByGoal[goal_id].saveState.save().columns, (col) => _.keys(col.sort).filter((key) => key !== 'ignoreSort').length + (_.get(col, 'filters[0].term', '') || '').length > 0);
        // check filter/sort columns. Cannot filter on both baseline and current. choose the more recent filter/sort
        grid_columns = remove_conflict_columns(grid_columns);
        // convert cycle columns to canonical columns
        const formatted_columns = format_cycle_columns(grid_columns);

        // inventory_service.saveGridSettings(`${localStorageKey}.sort`, {
        //     columns
        // });
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
                const { string, operator, value } = inventory_service.parseFilter(subFilter);
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
            // $scope.column_sorts.sort((a, b) => a.priority > b.priority);
          }
        }
        // $scope.isModified();
      };


      const set_grid_options = (goal) => {
        $scope.show_full_labels = { baseline: false, current: false };
        $scope.selected_ids = [];
        spinner_utility.hide();

        $scope.gridOptionsByGoal[goal] = {
          data: $scope.data_by_goal[goal],
          columnDefs: selected_columns(goal),
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
            action: () => $scope.gridApiByGoal[goal].exporter.csvExport('all', 'all')
          }],
          onRegisterApi: (gridApi) => {
            $scope.gridApiByGoal[goal] = gridApi;

            _.delay(() => $scope.updateHeight(goal), 150);

            const debouncedHeightUpdate = _.debounce(() => $scope.updateHeight(goal), 150);
            angular.element($window).on('resize', debouncedHeightUpdate);
            $scope.$on('$destroy', () => {
              angular.element($window).off('resize', debouncedHeightUpdate);
            });

            gridApi.core.on.sortChanged($scope, () => {
              spinner_utility.show();
              _.debounce(() => {
                updateColumnFilterSort(goal);
                load_data(1);
              }, 500)();
            });

            gridApi.core.on.filterChanged($scope, _.debounce(() => {
              spinner_utility.show();
              updateColumnFilterSort(goal);
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
        for (const goal in $scope.data_report.goals || []) {
          $scope.gridApiByGoal[goal] && $scope.gridApiByGoal[goal].core.refresh();
        }
      };
      $scope.reset_filters = () => {
        $scope.column_filters = [];
        for (const goal in $scope.data_report.goals || []) {
          $scope.gridApiByGoal[goal] && $scope.gridApiByGoal[goal].grid.clearAllFilters();
        }
      };

      $scope.select_all = (goal_id) => {
        // select all rows to visibly support everything has been selected
        $scope.gridApiByGoal[goal_id].selection.selectAllRows();
        $scope.selected_count = $scope.inventory_pagination.total;
        goal_service.get_goal($scope.goal0.id).then((response) => {
          const goal = response.data.goal;
          if (goal) {
            $scope.selected_ids = goal.current_cycle_property_view_ids;
          }
        });
      };

      $scope.select_none = (goal_id) => {
        $scope.gridApiByGoal[goal_id].selection.clearSelectedRows();
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
          for (const goal of $scope.data_report.goals) {
            $scope.gridApiByGoal[goal].selection.clearSelectedRows();
          }
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
            goal: () => $scope.goal0,
            question_options: () => $scope.question_options,
            write_permission: () => $scope.write_permission
          }
        });
        modalInstance.result.then(() => {
          // dialog was closed with 'Done' button.
          $scope.selected_option = 'none';
          $scope.selected_count = 0;
          for (const goal of $scope.data_report.goals) {
            $scope.gridApiByGoal[goal].selection.clearSelectedRows();
          }
          load_summary();
          load_data();
        });
      };

      // -------- SUMMARY LOGIC ------------

      const set_summary_grid_options = (summaries) => {
        $scope.summaryGridOptionsByGoal = {}
        $scope.summaryGridApiByGoal = {}
        $scope.summary_data_by_goal = {}
        
        for (const [goal_id, summary] of Object.entries(summaries)) {
          get_data_report_stats(summary);
          let column_defs;
          if ($scope.data_report.type === "standard") {
            $scope.summary_data_by_goal[goal_id] = goal_standard_service.format_summary(summary, $scope.data_report_details)
            column_defs = goal_standard_service.summary_column_defs($scope.goal0, area_units, eui_units)
          }

          const summaryGridOptions = {
            data: $scope.summary_data_by_goal[goal_id],
            columnDefs: column_defs,
            enableHorizontalScrollbar: uiGridConstants.scrollbars.WHEN_NEEDED,
            enableVerticalScrollbar: uiGridConstants.scrollbars.NEVER,
            enableSorting: false,
            minRowsToShow: 1,
            onRegisterApi: (gridApi) => {
              $scope.summaryGridApiByGoal[goal_id] = gridApi;
            }
          }
          $scope.summaryGridOptionsByGoal[goal_id] = summaryGridOptions;
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
            Notification.erorr('Unexpected Error');
          });
      };
    }]);
