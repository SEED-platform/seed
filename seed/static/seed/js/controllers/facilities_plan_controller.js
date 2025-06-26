/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.facilities_plan', [])
  .controller('facilities_plan_controller', [
    '$scope',
    '$window',
    '$translate',
    '$uibModal',
    '$state',
    'urls',
    'facilities_plans',
    'facilities_plan_runs',
    'access_level_tree',
    'property_columns',
    'auth_payload',
    'facilities_plan_run_service',
    'spinner_utility',
    'uiGridConstants',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $window,
      $translate,
      $uibModal,
      $state,
      urls,
      facilities_plans,
      facilities_plan_runs,
      access_level_tree,
      property_columns,
      auth_payload,
      facilities_plan_run_service,
      spinner_utility,
      uiGridConstants
    ) {
      $scope.auth = auth_payload.auth;
      // TODO: should we refactor to return facilities plan within facilities_plan_run response?
      $scope.facilities_plan_runs = facilities_plan_runs.data;
      $scope.facilities_plans = facilities_plans.data;
      $scope.current_facilities_plan_run_id = null;
      $scope.current_facilities_plan_run = null;
      $scope.current_facilities_plan = null;
      $scope.selected_count = 0;

      $scope.change_facilities_plan = (id) => {
        $scope.current_facilities_plan_run = $scope.facilities_plan_runs.find((fp) => fp.id === id);
        $scope.current_facilities_plan_run_id = id;
        // Store to localStorage
        localStorage.setItem(LAST_PLAN_RUN_ID_KEY, id);
        // also looking current facilities plan from current_facilities_plan_run.facilities_plan
        $scope.current_facilities_plan = $scope.facilities_plans.find((fp) => fp.id === $scope.current_facilities_plan_run?.facilities_plan);
        load_data(1); // get the first page of the selected run
      };

      const selected_columns = () => {
        const property_display_field = $scope.current_facilities_plan_run.property_display_field;
        return [
          {
            name: 'id',
            displayName: '',
            headerCellTemplate: '<span></span>', // remove header
            cellTemplate:
              '<div class="ui-grid-row-header-link">' +
              `  <a title="${$translate.instant(
                'Go to Detail Page'
              )}" class="ui-grid-cell-contents" ng-if="row.entity.$$treeLevel === 0" ui-sref="inventory_detail({inventory_type: 'properties', view_id: row.entity.property_view_id})">` +
              '    <i class="ui-grid-icon-info-circled"></i>' +
              '  </a>' +
              `  <a title="${$translate.instant(
                'Go to Detail Page'
              )}" class="ui-grid-cell-contents" ng-if="!row.entity.hasOwnProperty($$treeLevel)" ui-sref="inventory_detail({inventory_type: 'properties', view_id: row.entity.property_view_id})" >` +
              '    <i class="ui-grid-icon-info-circled"></i>' +
              '  </a>' +
              '</div>',
            enableColumnMenu: false,
            enableColumnMoving: false,
            enableColumnResizing: false,
            enableFiltering: true,
            enableHiding: false,
            enableSorting: false,
            exporterSuppressExport: true,
            pinnedLeft: true,
            visible: true,
            width: 30
          },
          {
            displayName: property_display_field.display_name ? property_display_field.display_name : property_display_field.column_name,
            name: `${property_display_field.column_name}_${property_display_field.id}`,
            cellClass: () => 'portfolio-summary-current-cell',
            enableFiltering: true,
            cellFilter: 'number'
          },
          ...Object.values($scope.current_facilities_plan_run.display_columns).map((c) => ({
            displayName: c.display_name && c.display_name !== '' ? c.display_name : c.column_name,
            name: `${c.column_name}_${c.id}`,
            enableFiltering: true
          })),
          ...Object.values($scope.current_facilities_plan_run.columns).map((c) => ({
            displayName: c.display_name && c.display_name !== '' ? c.display_name : c.column_name,
            name: `${c.column_name}_${c.id}`,
            enableFiltering: true
          })),
          { displayName: 'Total Energy Usage', name: 'total_energy_usage', enableFiltering: false },
          { displayName: 'Percentage Of Total Energy Usage', name: 'percentage_of_total_energy_usage', enableFiltering: false },
          { displayName: 'Running Percentage', name: 'running_percentage', enableFiltering: false },
          { displayName: 'Running Square Footage', name: 'running_square_footage', enableFiltering: false }
        ];
      };

      $scope.columnDisplayByName = {};
      for (const col of $scope.facilities_plan_runs.map((fpr) => Object.values(fpr.columns)).flat()) {
        $scope.columnDisplayByName[col.name] = col.displayName;
      }

      $scope.updateHeight = () => {
        let height = 0;
        for (const selector of ['.header', '.page_header_container', '.section_nav_container', '.grid-header']) {
          const [element] = angular.element(selector);
          height += element?.offsetHeight ?? 0;
        }
        angular.element('#portfolioSummary-gridOptions-wrapper').css('height', `calc(100vh - ${height}px)`);
        angular.element('#gridOptions').css('height', `calc(100vh - ${height}px)`);
        $scope.gridApi.core.handleWindowResize();
        $scope.gridApi.grid.refresh();
      };

      const load_data = (page) => {
        if ($scope.current_facilities_plan_run_id === undefined) return;

        $scope.data_loading = true;
        const per_page = 100;
        const data = {
          page,
          per_page
        };
        const column_filters = $scope.column_filters;
        const order_by = $scope.column_sorts;
        facilities_plan_run_service.get_facilities_plan_run_properties($scope.current_facilities_plan_run_id, data, column_filters, order_by).then((data) => {
          $scope.inventory_pagination = data.pagination;
          $scope.data = data.properties;
          // get_all_labels();
          // console.log($scope.data)
          set_grid_options();
          $scope.data_valid = Boolean(data.properties);
          $scope.data_loading = false;
        });
      };

      const set_grid_options = () => {
        $scope.selected_ids = [];
        spinner_utility.hide();
        $scope.gridOptions = {
          data: 'data',
          columnDefs: selected_columns(),
          rowTemplate:
            `<div ng-style="grid.appScope.getRowStyle(row)" ng-repeat="(colRenderIndex, col) in colContainer.renderedColumns track by col.colDef.name"
              class="ui-grid-cell" ui-grid-cell></div>`,
          enableFiltering: true,
          enableSorting: true,
          useExternalFiltering: true,
          useExternalSorting: true,
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

            const debouncedHeightUpdate = _.debounce($scope.updateHeight, 150);
            angular.element($window).on('resize', debouncedHeightUpdate);
            $scope.$on('$destroy', () => {
              angular.element($window).off('resize', debouncedHeightUpdate);
            });

            const selectionChanged = () => {
              console.log(gridApi.selection.getSelectedRows());
              $scope.selected_ids = gridApi.selection.getSelectedRows().map((row) => row.property_view_id);
              $scope.selected_count = $scope.selected_ids.length;
              console.log($scope.selected_ids);
            };
            gridApi.selection.on.rowSelectionChanged($scope, selectionChanged);
            gridApi.selection.on.rowSelectionChangedBatch($scope, selectionChanged);
          }
        };
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

      // const operatorLookup = {
      //   ne: '!=',
      //   exact: '=',
      //   lt: '<',
      //   lte: '<=',
      //   gt: '>',
      //   gte: '>=',
      //   icontains: ''
      // };
      const operatorArr = ['>', '<', '=', '!', '!=', '<=', '>='];

      const updateColumnFilterSort = () => {
        const columns = _.filter($scope.gridApi.saveState.save().columns, (col) => _.keys(col.sort).filter((key) => key !== 'ignoreSort').length + (_.get(col, 'filters[0].term', '') || '').length > 0);

        // inventory_service.saveGridSettings(`${localStorageKey}.sort`, {
        //   columns
        // });

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
      };

      $scope.getRowStyle = (row) => {
        const val = row.entity.running_percentage;
        if (val !== null && val <= $scope.current_facilities_plan.energy_running_sum_percentage) {
          return { background: '#d4edda' }; // light green
        }
        return {};
      };

      $scope.page_change = (page) => {
        spinner_utility.show();
        load_data(page);
      };

      /**
       Opens a modal to batch edit goal notes
       */
      $scope.open_bulk_edit_properties_modal = () => {
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/bulk_edit_properties_modal.html`,
          controller: 'bulk_edit_properties_modal_controller',
          resolve: {
            property_view_ids: () => $scope.selected_ids,
            compliance_cycle_year_column: () => $scope.current_facilities_plan_run.columns.compliance_cycle_year_column,
            include_in_total_denominator_column: () => $scope.current_facilities_plan_run.columns.include_in_total_denominator_column,
            exclude_from_plan_column: () => $scope.current_facilities_plan_run.columns.exclude_from_plan_column,
            require_in_plan_column: () => $scope.current_facilities_plan_run.columns.require_in_plan_column
          }
        });

        modalInstance.result.then(() => {
          // dialog was closed with 'Done' button.
          $scope.selected_option = 'none';
          $scope.selected_count = 0;
          $scope.gridApi.selection.clearSelectedRows();
          // load_summary();
          load_data();
        });
      };

      $scope.delete_facilities_plan_run = () => {
        // console.log('delete_facilties_plan');
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/delete_facilities_plan_run_modal.html`,
          controller: 'delete_facilities_plan_run_modal_controller',
          resolve: {
            facilities_plan_run: () => $scope.current_facilities_plan_run
          }
        });
      };

      $scope.update_facilities_plan_run = () => {
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/create_facilities_plan_run_modal.html`,
          controller: 'create_facilities_plan_run_modal_controller',
          resolve: {
            access_level_tree: () => access_level_tree,
            facilities_plans: () => facilities_plans.data,
            columns: () => property_columns,
            existing_fpr: () => $scope.current_facilities_plan_run,
            level_name_index: () => access_level_tree.access_level_names.findIndex((n) => n === $scope.current_facilities_plan_run.ali_level)
          }
        });
      };

      /**
       Opens a modal to create facilities plan run
      * */
      $scope.create_facilities_plan_run = () => {
        $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/create_facilities_plan_run_modal.html`,
          controller: 'create_facilities_plan_run_modal_controller',
          resolve: {
            access_level_tree: () => access_level_tree,
            facilities_plans: () => facilities_plans.data,
            columns: () => property_columns,
            existing_fpr: () => null,
            level_name_index: () => null
          }
        });
      };

      $scope.select_all = () => {
        // select all rows to visibly support everything has been selected
        $scope.gridApi.selection.selectAllRows();
        $scope.selected_count = $scope.inventory_pagination.total;
        facilities_plan_run_service.get_all_ids($scope.current_facilities_plan_run_id, $scope.column_filters).then((response) => {
          $scope.selected_ids = response.ids;
        });
      };

      $scope.select_none = () => {
        $scope.gridApi.selection.clearSelectedRows();
        $scope.selected_count = 0;
        $scope.update_selected_display();
      };

      $scope.run_the_run = () => {
        spinner_utility.show();
        facilities_plan_run_service.run_the_run($scope.current_facilities_plan_run_id).then(() => {
          $state.reload();
        });
      };

      // Key for localStorage
      const LAST_PLAN_RUN_ID_KEY = 'last_facilities_plan_run_id';
      const lastSelectedId = localStorage.getItem(LAST_PLAN_RUN_ID_KEY);
      // initialize the current facilities plan run
      if (lastSelectedId && $scope.facilities_plan_runs.some((fp) => fp.id === Number(lastSelectedId))) {
        $scope.change_facilities_plan(Number(lastSelectedId));
      } else if ($scope.facilities_plan_runs) {
        // use first one if nothing in storage
        $scope.change_facilities_plan($scope.facilities_plan_runs[0]?.id);
      }
    }]);
