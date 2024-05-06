/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * This controller handles the inventory reports page, watching for and remembering
 * the user's selections for chart parameters like date range and x and y variables,
 * and then updating the chart directives when the user clicks the update chart button.
 */

angular.module('BE.seed.controller.inventory_reports', []).controller('inventory_reports_controller', [
  '$scope',
  '$log',
  '$stateParams',
  'spinner_utility',
  'inventory_reports_service',
  'simple_modal_service',
  'columns',
  'cycles',
  'organization_payload',
  'urls',
  '$sce',
  '$translate',
  '$uibModal',
  'ah_service',
  'access_level_tree',
  'user_service',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $log,
    $stateParams,
    spinner_utility,
    inventory_reports_service,
    simple_modal_service,
    columns,
    cycles,
    organization_payload,
    urls,
    $sce,
    $translate,
    $uibModal,
    ah_service,
    access_level_tree,
    user_service
  ) {
    const org_id = organization_payload.organization.id;
    const base_storage_key = `report.${org_id}`;

    $scope.access_level_tree = access_level_tree.access_level_tree;
    $scope.level_names = access_level_tree.access_level_names;
    $scope.level_name_index = null;
    $scope.potential_level_instances = [];
    $scope.access_level_instance_id = null;
    $scope.users_access_level_instance_id = user_service.get_access_level_instance().id;

    const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);
    // cannot select parents alis
    const [users_depth, ] = Object.entries(access_level_instances_by_depth).find(([, x]) => x.length === 1 && x[0].id === parseInt($scope.users_access_level_instance_id, 10));
    $scope.level_names = access_level_tree.access_level_names.slice(users_depth - 1);

    $scope.change_selected_level_index = () => {
      const new_level_instance_depth = parseInt($scope.level_name_index, 10) + parseInt(users_depth, 10);
      $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
      $scope.access_level_instance_id = null;
    };

    const pretty_unit = (pint_spec) => {
      const mappings = {
        'ft**2': 'ft²',
        'm**2': 'm²',
        'kBtu/ft**2/year': 'kBtu/sq. ft./year',
        'GJ/m**2/year': 'GJ/m²/year',
        'MJ/m**2/year': 'MJ/m²/year',
        'kWh/m**2/year': 'kWh/m²/year',
        'kBtu/m**2/year': 'kBtu/m²/year'
      };
      return mappings[pint_spec] || pint_spec;
    };

    const eui_units = () => {
      const unit = organization_payload.organization.display_units_eui;
      return pretty_unit(unit);
    };

    const area_units = () => {
      const unit = organization_payload.organization.display_units_area;
      return pretty_unit(unit);
    };

    /* Define the first five colors. After that, rely on Dimple's default colors. */
    $scope.defaultColors = ['#458cc8', '#779e1c', '#f2c41d', '#939495', '#c83737', '#f18630'];

    /* Setup models from "From" and "To" selectors */
    $scope.cycles = cycles.cycles;

    const translateAxisLabel = (label, units) => {
      let str = '';
      str += $translate.instant(label);
      if (units) {
        str += ` (${$translate.instant(units)})`;
      }
      return str;
    };

    const parse_axis_label = (column) => {
      if (column.column_name.includes('eui')) {
        return translateAxisLabel(column.displayName, eui_units());
      }
      if (column.column_name.includes('area')) {
        return translateAxisLabel(column.displayName, area_units());
      }
      return $translate.instant(column.displayName);
    };

    /* SCOPE VARS */
    /* ~~~~~~~~~~ */

    /** Chart variables :
       These next two scoped arrays, $scope.xAxisVars and $scope.yAxisVars, define the various properties
       of the variables the user can select for graphing.

       Each object contains information used by the dropdown controls.

       $scope.xAxisVars consists of columns specified as numeric types.

       $scope.uAxisVars consists of manually defined columns specified.
       Ideally, if we need to add new variables, we should just be able to add a new object to
       either of these arrays. (However, at first when adding new variables we might need to add
       new functionality to the directive to handle any idiosyncrasies of graphing that new variable.)
       */

    const acceptable_column_types = ['area', 'eui', 'float', 'integer', 'number'];

    const filtered_columns = _.filter(columns, (column) => _.includes(acceptable_column_types, column.data_type));

    $scope.xAxisVars = [
      {
        name: 'Count',
        label: 'Count',
        varName: 'Count',
        axisLabel: 'Count'
      },
      ..._.map(filtered_columns, (column) => ({
        name: $translate.instant(column.displayName), // short name for variable, used in pulldown
        label: $translate.instant(column.displayName), // full name for variable
        varName: column.column_name, // name of variable, to be sent to server
        axisLabel: parse_axis_label(column) // label to be used in charts, should include units
      // axisType: 'Measure', //DimpleJS property for axis type
      // axisTickFormat: ',.0f' //DimpleJS property for axis tick format
      }))
    ];

    const acceptable_y_column_names = ['gross_floor_area', 'property_type', 'year_built'];
    const filtered_y_columns = _.filter(columns, (column) => _.includes(acceptable_y_column_names, column.column_name));

    $scope.yAxisVars = _.map(filtered_y_columns, (column) => ({
      name: $translate.instant(column.displayName), // short name for variable, used in pulldown
      label: $translate.instant(column.displayName), // full name for variable
      varName: column.column_name, // name of variable, to be sent to server
      axisLabel: parse_axis_label(column) // label to be used in charts, should include units
      // axisType: 'Measure', //DimpleJS property for axis type
      // axisTickFormat: ',.0f' //DimpleJS property for axis tick format
    }));

    // Chart titles
    $scope.chart1Title = '';
    $scope.chart2Title = '';

    // Series
    // the following variable keeps track of which
    // series will be sent to the graphs when data is updated
    // ('series' values are used by the dimple graphs to group data)
    $scope.chartSeries = ['id', 'yr_e'];
    $scope.aggChartSeries = ['property_type', 'yr_e'];

    const localStorageXAxisKey = `${base_storage_key}.xaxis`;
    const localStorageYAxisKey = `${base_storage_key}.yaxis`;
    const localStorageALIndex = `${base_storage_key}.ALIndex`;
    const localStorageALIID = `${base_storage_key}.ALIID`;

    // Currently selected x and y variables - check local storage first, otherwise initialize to first choice
    $scope.xAxisSelectedItem = JSON.parse(localStorage.getItem(localStorageXAxisKey)) || $scope.xAxisVars[0];
    $scope.yAxisSelectedItem = JSON.parse(localStorage.getItem(localStorageYAxisKey)) || $scope.yAxisVars[0];

    $scope.level_name_index = JSON.parse(localStorage.getItem(localStorageALIndex)) || '0';
    const new_level_instance_depth = parseInt($scope.level_name_index, 10) + parseInt(users_depth, 10);
    $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
    $scope.access_level_instance_id = JSON.parse(localStorage.getItem(localStorageALIID)) || parseInt($scope.users_access_level_instance_id, 10);

    // Chart data
    $scope.chartData = [];
    $scope.aggChartData = [];
    $scope.pointBackgroundColors = [];
    $scope.aggPointBackgroundColors = [];

    // Chart status
    $scope.chartIsLoading = false;
    $scope.aggChartIsLoading = false;

    // Setting the status messages will cause the small white status box to show above the chart
    // Setting these to empty string will remove that box
    $scope.chartStatusMessage = 'No Data';
    $scope.aggChartStatusMessage = 'No Data';

    /* NEW CHART STUFF */
    const createChart = (elementId, type, indexAxis, pointColors) => {
      const canvas = document.getElementById(elementId);
      const ctx = canvas.getContext('2d');

      return new Chart(ctx, {
        type,
        data: {
          datasets: [
            {
              data: [],
              pointBackgroundColor: pointColors,
              backgroundColor: pointColors
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          layout: {
            padding: 20
          },
          indexAxis,
          scales: {
            x: {
              display: true,
              title: {
                display: true
              }
            },
            y: {
              display: true,
              title: {
                display: true
              },
              ticks: {
                // round values
                callback(value) {
                  return this.getLabelForValue(value);
                }
              }
            }
          },
          elements: {
            point: {
              radius: 5,
              backgroundColor: '#458CC8'
            },
            bar: {
              backgroundColor: '#458CC8'
            }
          },
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              // add in the pop up tool tips to show the datapoint values
              displayColors: false,
              mode: 'index',
              callbacks: {
                label(ctx) {
                  const label = [];
                  const labeltmp = $scope.chartData.chartData.filter((entry) => entry.id === ctx.raw.id);
                  if (labeltmp.length > 0) {
                    label.push(`${$scope.yAxisSelectedItem.label}: ${ctx.formattedValue}`);
                    // The x axis data is generated more programmatically than the y, so only
                    // grab the `label` since the `axisLabel` has redundant unit information.
                    label.push(`${$scope.xAxisSelectedItem.label}: ${ctx.parsed.x}`);
                  }
                  return label;
                }
              }
            }
          }
        }
      });
    };

    $scope.scatterChart = createChart('chartNew', 'scatter', 'x', $scope.pointBackgroundColors);

    $scope.barChart = createChart('aggChartNew', 'bar', 'y', $scope.aggPointBackgroundColors);

    // specific styling for bar chart
    $scope.barChart.options.scales.x.ticks = { precision: 0 };
    $scope.barChart.options.scales.y.type = 'category';
    $scope.barChart.options.scales.y.ticks = {};

    // specific styling for scatter chart
    $scope.scatterChart.options.scales.x.suggestedMin = 0;

    $scope.cycle_selection = '';
    $scope.selected_cycles = [];
    $scope.available_cycles = () => $scope.cycles.filter(({ id }) => !$scope.selected_cycles.includes(id));
    $scope.select_cycle = () => {
      const selection = $scope.cycle_selection;
      $scope.cycle_selection = '';
      if (!$scope.selected_cycles) {
        $scope.selected_cycles = [];
      }
      $scope.selected_cycles.push(selection);
    };

    $scope.get_cycle_display = (id) => {
      const record = _.find($scope.cycles, { id });
      if (record) {
        return record.name;
      }
    };

    $scope.click_remove_cycle = (id) => {
      $scope.selected_cycles = $scope.selected_cycles.filter((item) => item !== id);
    };

    /* END NEW CHART STUFF */

    /* UI HANDLERS */
    /* ~~~~~~~~~~~ */

    /* Update data used by the chart. This will force the charts to re-render */
    $scope.updateChartData = () => {
      // TODO Form check, although at the moment it's just four selects so user shouldn't be able to get form into an invalid state. */

      // if ($scope.invalidDates) {
      //   //Show a basic error modal
      //   const modalOptions = {
      //     type: 'error',
      //     okButtonText: 'OK',
      //     cancelButtonText: null,
      //     headerText: 'Invalid Dates',
      //     bodyText: 'The \'From\' date must be before the \'To\' date'
      //   };
      //   simple_modal_service.showModal(modalOptions).then(function (result) {
      //       $log.info('result', result);
      //     },
      //     function (result) {
      //       $log.info('error', result);
      //     });
      //   return;
      // }

      clearChartData();
      $scope.chartStatusMessage = 'Loading data...';
      $scope.aggChartStatusMessage = 'Loading data...';
      getChartData();
      getAggChartData();
      updateChartTitlesAndAxes();
      updateStorage();
    };

    /* FLAGS FOR CHART STATE */
    /* ~~~~~~~~~~~~~~~~~~~~~ */

    /* The directive will call this, so we can update our flag for the state of the chart. */
    $scope.chartRendered = () => {
      $scope.chartIsLoading = false;
    };

    /* The directive will call this, so we can update our flag for the state of the chart. */
    $scope.aggChartRendered = () => {
      $scope.aggChartIsLoading = false;
    };

    /* PRIVATE FUNCTIONS (so to speak) */
    /* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

    /* Clear the data used by the chart */
    function clearChartData() {
      $scope.chartData = [];
      $scope.aggChartData = [];
      $scope.propertyCounts = [];
      $scope.aggPropertyCounts = [];
      $scope.pointBackgroundColors.length = 0;
      $scope.aggPointBackgroundColors.length = 0;
    }

    /* Update the titles above each chart */
    function updateChartTitlesAndAxes() {
      let interpolationParams;
      try {
        interpolationParams = {
          x_axis_label: $translate.instant($scope.xAxisSelectedItem.label),
          y_axis_label: $translate.instant($scope.yAxisSelectedItem.label)
        };
      } catch (e) {
        $log.error('$sce issue... missing translation');
        interpolationParams = {
          x_axis_label: $scope.xAxisSelectedItem.label,
          y_axis_label: $scope.yAxisSelectedItem.label
        };
      }
      $scope.chart1Title = $translate.instant('X_VERSUS_Y', interpolationParams);
      $scope.chart2Title = $translate.instant('X_VERSUS_Y_AGGREGATED', interpolationParams);

      $scope.scatterChart.options.scales.x.title.text = $scope.xAxisSelectedItem.label;
      $scope.scatterChart.options.scales.y.title.text = $scope.yAxisSelectedItem.label;

      $scope.barChart.options.scales.x.title.text = $scope.xAxisSelectedItem.label;
      $scope.barChart.options.scales.y.title.text = $scope.yAxisSelectedItem.label;
    }

    $scope.open_export_modal = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/export_report_modal.html`,
        controller: 'export_report_modal_controller',
        resolve: {
          axes_data: () => ({
            xVar: $scope.chartData.xAxisVarName,
            xLabel: $scope.chartData.xAxisTitle,
            yVar: $scope.chartData.yAxisVarName,
            yLabel: $scope.chartData.yAxisTitle
          }),
          cycles: () => $scope.selected_cycles
        }
      });
      modalInstance.result.finally(spinner_utility.hide);
    };

    /** Get the 'raw' (disaggregated) chart data from the server for the scatter plot chart.
       The user's selections are already stored as properties on the scope, so use
       those for the parameters that need to be sent to the server.

       When chart data is returned from the service, pass it to our chart directive along
       with configuration information. The chart will update automatically as it's watching the
       chartData property on the scope.

       In the future, if we want the chart to look or behave differently depending on the data,
       we can pass in different configuration options.
       The chart will update automatically as it's watching the chartData property on the scope.
       */
    function getChartData() {
      const xVar = $scope.xAxisSelectedItem.varName;
      const yVar = $scope.yAxisSelectedItem.varName;
      $scope.chartIsLoading = true;

      inventory_reports_service
        .get_report_data(xVar, yVar, $scope.selected_cycles, $scope.access_level_instance_id)
        .then(
          (data) => {
            data = data.data;
            const propertyCounts = data.property_counts;
            const colorsArr = mapColors(propertyCounts);
            $scope.propertyCounts = propertyCounts;
            $scope.chartData = {
              series: $scope.chartSeries,
              chartData: data.chart_data,
              xAxisTitle: $scope.xAxisSelectedItem.axisLabel,
              xAxisVarName: $scope.xAxisSelectedItem.varName,
              yAxisTitle: $scope.yAxisSelectedItem.axisLabel,
              yAxisVarName: $scope.yAxisSelectedItem.varName,
              yAxisType: $scope.yAxisSelectedItem.axisType,
              yAxisMin: $scope.yAxisSelectedItem.axisMin,
              xAxisTickFormat: $scope.xAxisSelectedItem.axisTickFormat,
              yAxisTickFormat: $scope.yAxisSelectedItem.axisTickFormat
            };

            // new chartJS chart data
            $scope.scatterChart.options.scales.y.min = $scope.yAxisSelectedItem.axisMin;
            $scope.scatterChart.options.scales.y.type = $scope.chartData.chartData.every((d) => typeof d.y === 'number') ? 'linear' : 'category';
            $scope.scatterChart.data.datasets[0].data = $scope.chartData.chartData;
            // add the colors to the datapoints, need to create a hash map first
            const colorMap = new Map(colorsArr.map((object) => [object.seriesName, object.color]));
            for (let i = 0; i < $scope.scatterChart.data.datasets[0].data.length; i++) {
              $scope.pointBackgroundColors.push(colorMap.get($scope.scatterChart.data.datasets[0].data[i].yr_e));
            }
            $scope.scatterChart.update();

            if ($scope.chartData.chartData && $scope.chartData.chartData.length > 0) {
              $scope.chartStatusMessage = '';
            } else {
              $scope.chartStatusMessage = 'No Data';
            }
          },
          (data, status) => {
            $scope.chartStatusMessage = 'Data Load Error';
            $log.error(`#InventoryReportsController: Error loading chart data : ${status}`);
          }
        )
        .finally(() => {
          $scope.chartIsLoading = false;
        });
    }

    /** Get the aggregated chart data from the server for the scatter plot chart.
       The user's selections are already stored as properties on the scope, so use
       those for the parameters that need to be sent to the server.

       When chart data is returned from the service, pass it to our chart directive along
       with configuration information. The chart will update automatically as it's watching the
       chartData property on the scope.

       In the future, if we want the chart to look or behave differently depending on the data,
       we can pass in different configuration options.

       * */
    function getAggChartData() {
      const xVar = $scope.xAxisSelectedItem.varName;
      const yVar = $scope.yAxisSelectedItem.varName;
      $scope.aggChartIsLoading = true;
      inventory_reports_service
        .get_aggregated_report_data(xVar, yVar, $scope.selected_cycles, $scope.access_level_instance_id)
        .then(
          (data) => {
            data = data.aggregated_data;
            $scope.aggPropertyCounts = data.property_counts;
            const propertyCounts = data.property_counts;
            const colorsArr = mapColors(propertyCounts);
            $scope.aggPropertyCounts = propertyCounts;
            $scope.aggChartData = {
              series: $scope.aggChartSeries,
              chartData: data.chart_data
            };

            // new agg chart
            const the_data = _.orderBy($scope.aggChartData.chartData, ['y'], ['desc']);
            $scope.barChart.data.labels = the_data.map((a) => a.y);
            $scope.barChart.data.datasets[0].data = the_data.map((a) => a.x);
            // add the colors to the datapoints, need to create a hash map first
            const colorMap = new Map(colorsArr.map((object) => [object.seriesName, object.color]));
            for (let i = 0; i < the_data.length; i++) {
              $scope.aggPointBackgroundColors.push(colorMap.get(the_data[i].yr_e));
            }
            $scope.barChart.update();

            if (!_.isEmpty($scope.aggChartData.chartData)) {
              $scope.aggChartStatusMessage = '';
            } else {
              $scope.aggChartStatusMessage = 'No Data';
            }
          },
          (data, status) => {
            $scope.aggChartStatusMessage = 'Data Load Error';
            $log.error(`#InventoryReportsController: Error loading agg chart data : ${status}`);
          }
        )
        .finally(() => {
          $scope.aggChartIsLoading = false;
        });
    }

    function updateStorage() {
      // Save axis and cycle selections
      localStorage.setItem(localStorageXAxisKey, JSON.stringify($scope.xAxisSelectedItem));
      localStorage.setItem(localStorageYAxisKey, JSON.stringify($scope.yAxisSelectedItem));
      localStorage.setItem(localStorageSelectedCycles, JSON.stringify($scope.selected_cycles));
      localStorage.setItem(localStorageALIndex, JSON.stringify($scope.level_name_index));
      localStorage.setItem(localStorageALIID, JSON.stringify($scope.access_level_instance_id));
    }

    /*  Generate an array of color objects to be used as part of chart configuration
       Each color object should have the following properties:
       {
       seriesName:  A string value for the name of the series
       color:       A hex value for the color
       }
       A side effect of this method is that the colors are also applied to the propertyCounts object
       so that they're available in the table view beneath the chart that lists group details.
       */
    function mapColors(propertyCounts) {
      if (!propertyCounts) return [];
      const colorsArr = [];
      const numPropertyGroups = propertyCounts.length;
      for (let groupIndex = 0; groupIndex < numPropertyGroups; groupIndex++) {
        const obj = {
          color: $scope.defaultColors[groupIndex],
          seriesName: propertyCounts[groupIndex].yr_e
        };
        propertyCounts[groupIndex].color = obj.color;
        colorsArr.push(obj);
      }
      // propertyCounts.reverse(); //so the table/legend order matches the order Dimple will build the groups
      return colorsArr;
    }

    const localStorageSelectedCycles = `${base_storage_key}.SelectedCycles`;

    /* Call the update method so the page initializes
       with the values set in the scope */
    const init = () => {
      // Initialize pulldowns
      $scope.selected_cycles = JSON.parse(localStorage.getItem(localStorageSelectedCycles)) || [];

      // Attempt to load selections
      $scope.updateChartData();
    };

    init();
  }
]);
