/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 This controller handles the inventory reports page, watching for and remembering
 the user's selections for chart parameters like date range and x and y variables,
 and then updating the chart directives when the user clicks the update chart button.
 */

angular.module('BE.seed.controller.inventory_reports', [])
  .controller('inventory_reports_controller', [
    '$scope',
    '$log',
    '$stateParams',
    'inventory_reports_service',
    'simple_modal_service',
    'columns',
    'cycles',
    'organization_payload',
    'flippers',
    'urls',
    '$sce',
    '$translate',
    '$uibModal',
    function (
      $scope,
      $log,
      $stateParams,
      inventory_reports_service,
      simple_modal_service,
      columns,
      cycles,
      organization_payload,
      flippers,
      urls,
      $sce,
      $translate,
      $uibModal
    ) {
      $scope.inventory_type = $stateParams.inventory_type;

      var org_id = organization_payload.organization.id;
      var base_storage_key = 'report.' + org_id + '.' + $scope.inventory_type;

      var pretty_unit = function (pint_spec) {
        var mappings = {
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

      var eui_units = function () {
        var unit = organization_payload.organization.display_units_eui;
        return pretty_unit(unit);
      };

      var area_units = function () {
        var unit = organization_payload.organization.display_units_area;
        return pretty_unit(unit);
      };

      /* Define the first five colors. After that, rely on Dimple's default colors. */
      $scope.defaultColors = ['#458cc8', '#779e1c', '#f2c41d', '#939495', '#c83737', '#f18630'];

      /* Setup models from "From" and "To" selectors */
      $scope.cycles = cycles.cycles;

      /* Model for pulldowns, initialized in init below */
      $scope.fromCycle = {};
      $scope.toCycle = {};

      var translateAxisLabel = function (label, units) {
        var str = '';
        str += $translate.instant(label);
        if (units) {
          str += ' (' + $translate.instant(units) + ')';
        }
        return str;
      };

      var parse_axis_label = function (column) {
        if (column.column_name.includes('eui')) {
          return translateAxisLabel(column.displayName, eui_units());
        } else if (column.column_name.includes('area')) {
          return translateAxisLabel(column.displayName, area_units());
        } else {
          return $translate.instant(column.displayName);
        }
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

      var acceptable_column_types = [
        'area',
        'eui',
        'float',
        'integer',
        'number'
      ];
      var filtered_columns = _.filter(columns, function (column) {
        return _.includes(acceptable_column_types, column.data_type);
      });

      $scope.xAxisVars = _.map(filtered_columns, function (column) {
        return {
          name: $translate.instant(column.displayName), //short name for variable, used in pulldown
          label: $translate.instant(column.displayName), //full name for variable
          varName: column.column_name, //name of variable, to be sent to server
          axisLabel: parse_axis_label(column), //label to be used in charts, should include units
          axisType: 'Measure', //DimpleJS property for axis type
          axisTickFormat: ',.0f' //DimpleJS property for axis tick format
        };
      });

      $scope.yAxisVars = [
        {
          name: $translate.instant('Gross Floor Area'),
          label: $translate.instant('Gross Floor Area'),
          varName: 'gross_floor_area',
          axisLabel: translateAxisLabel('Gross Floor Area', area_units()),
          axisTickFormat: ',.0f',
          axisType: 'Measure',
          axisMin: ''
        }, {
          name: $translate.instant('Property Classification'),
          label: $translate.instant('Property Classification'),
          varName: 'use_description',
          axisLabel: translateAxisLabel('Property Classification'),
          axisTickFormat: '',
          axisType: 'Category',
          axisMin: ''
        }, {
          name: $translate.instant('Year Built'),
          label: $translate.instant('Year Built'),
          varName: 'year_built',
          axisLabel: translateAxisLabel('Year Built'),
          axisTickFormat: '.0f',
          axisType: 'Measure',
          axisMin: '1900'
        }
      ];

      // Chart titles
      $scope.chart1Title = '';
      $scope.chart2Title = '';

      // Datepickers
      var initStartDate = new Date();
      initStartDate.setYear(initStartDate.getFullYear() - 1);
      $scope.startDate = initStartDate;
      $scope.startDatePickerOpen = false;
      $scope.endDate = new Date();
      $scope.endDatePickerOpen = false;
      $scope.invalidDates = false; // set this to true when startDate >= endDate;

      // Series
      // the following variable keeps track of which
      // series will be sent to the graphs when data is updated
      // ('series' values are used by the dimple graphs to group data)
      $scope.chartSeries = ['id', 'yr_e'];
      $scope.aggChartSeries = ['use_description', 'yr_e'];

      var localStorageXAxisKey = base_storage_key + '.xaxis';
      var localStorageYAxisKey = base_storage_key + '.yaxis';

      //Currently selected x and y variables - check local storage first, otherwise initialize to first choice
      $scope.xAxisSelectedItem = JSON.parse(localStorage.getItem(localStorageXAxisKey)) || $scope.xAxisVars[0];
      $scope.yAxisSelectedItem = JSON.parse(localStorage.getItem(localStorageYAxisKey)) || $scope.yAxisVars[0];

      //Chart data
      $scope.chartData = [];
      $scope.aggChartData = [];

      //Chart status
      $scope.chartIsLoading = false;
      $scope.aggChartIsLoading = false;

      //Setting the status messages will cause the small white status box to show above the chart
      //Setting these to empty string will remove that box
      $scope.chartStatusMessage = 'No Data';
      $scope.aggChartStatusMessage = 'No Data';


      /* UI HANDLERS */
      /* ~~~~~~~~~~~ */

      // Handle datepicker open/close events
      $scope.openStartDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.startDatePickerOpen = !$scope.startDatePickerOpen;
      };
      $scope.openEndDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.endDatePickerOpen = !$scope.endDatePickerOpen;
      };

      $scope.$watch('startDate', function () {
        $scope.checkInvalidDate();
      });

      $scope.$watch('endDate', function () {
        $scope.checkInvalidDate();
      });

      $scope.checkInvalidDate = function () {
        $scope.invalidDates = ($scope.endDate < $scope.startDate);
      };

      /* Update data used by the chart. This will force the charts to re-render*/
      $scope.updateChartData = function () {

        // TODO Form check, although at the moment it's just four selects so user shouldn't be able to get form into an invalid state. */


        // if ($scope.invalidDates) {
        //   //Show a basic error modal
        //   var modalOptions = {
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
        updateChartTitles();
        updateStorage();
      };


      /* FLAGS FOR CHART STATE */
      /* ~~~~~~~~~~~~~~~~~~~~~ */

      /* The directive will call this, so we can update our flag for the state of the chart. */
      $scope.chartRendered = function () {
        $scope.chartIsLoading = false;
      };

      /* The directive will call this, so we can update our flag for the state of the chart. */
      $scope.aggChartRendered = function () {
        $scope.aggChartIsLoading = false;
      };


      /* PRIVATE FUNCTIONS (so to speak) */
      /* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

      /* Clear the data used by the chart*/
      function clearChartData () {
        $scope.chartData = [];
        $scope.aggChartData = [];
        $scope.propertyCounts = [];
        $scope.aggPropertyCounts = [];
      }

      /* Update the titles above each chart*/
      function updateChartTitles () {
        var interpolationParams;
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
      }

      $scope.open_export_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/export_report_modal.html',
          controller: 'export_report_modal_controller',
          resolve: {
            axes_data: function () {
              return {
                xVar: $scope.chartData.xAxisVarName,
                xLabel: $scope.chartData.xAxisTitle,
                yVar: $scope.chartData.yAxisVarName,
                yLabel: $scope.chartData.yAxisTitle,
              };
            },
            cycle_start: function () {
              return $scope.fromCycle.selected_cycle.start;
            },
            cycle_end: function () {
              return $scope.toCycle.selected_cycle.end;
            },
          }
        });
      };

      /** Get the 'raw' (unaggregated) chart data from the server for the scatter plot chart.
       The user's selections are already stored as properties on the scope, so use
       those for the parameters that need to be sent to the server.

       When chart data is returned from the service, pass it to our chart directive along
       with configuration information. The chart will update automatically as it's watching the
       chartData property on the scope.

       In the future, if we want the chart to look or behave differently depending on the data,
       we can pass in different configuration options.
       The chart will update automatically as it's watching the chartData property on the scope.
       */
      function getChartData () {
        var xVar = $scope.xAxisSelectedItem.varName;
        var yVar = $scope.yAxisSelectedItem.varName;
        $scope.chartIsLoading = true;

        inventory_reports_service.get_report_data(xVar, yVar, $scope.fromCycle.selected_cycle.start, $scope.toCycle.selected_cycle.end)
          .then(function (data) {
            data = data.data;
            var propertyCounts = data.property_counts;
            var colorsArr = mapColors(propertyCounts);
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
              yAxisTickFormat: $scope.yAxisSelectedItem.axisTickFormat,
              colors: colorsArr
            };
            if ($scope.chartData.chartData && $scope.chartData.chartData.length > 0) {
              $scope.chartStatusMessage = '';
            } else {
              $scope.chartStatusMessage = 'No Data';
            }
          },
          function (data, status) {
            $scope.chartStatusMessage = 'Data Load Error';
            $log.error('#InventoryReportsController: Error loading chart data : ' + status);
          })
          .finally(function () {
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

       **/
      function getAggChartData () {

        var xVar = $scope.xAxisSelectedItem.varName;
        var yVar = $scope.yAxisSelectedItem.varName;
        $scope.aggChartIsLoading = true;
        inventory_reports_service.get_aggregated_report_data(
          xVar, yVar,
          $scope.fromCycle.selected_cycle.start,
          $scope.toCycle.selected_cycle.end
        ).then(function (data) {
          data = data.aggregated_data;
          console.log(data);
          $scope.aggPropertyCounts = data.property_counts;
          var propertyCounts = data.property_counts;
          var colorsArr = mapColors(propertyCounts);
          $scope.aggPropertyCounts = propertyCounts;
          $scope.aggChartData = {
            series: $scope.aggChartSeries,
            chartData: data.chart_data,
            xAxisTitle: $scope.xAxisSelectedItem.axisLabel,
            yAxisTitle: $scope.yAxisSelectedItem.axisLabel,
            yAxisType: 'Category',
            colors: colorsArr
          };
          if (!_.isEmpty($scope.aggChartData.chartData)) {
            $scope.aggChartStatusMessage = '';
          } else {
            $scope.aggChartStatusMessage = 'No Data';
          }
        },
        function (data, status) {
          $scope.aggChartStatusMessage = 'Data Load Error';
          $log.error('#InventoryReportsController: Error loading agg chart data : ' + status);
        })
          .finally(function () {
            $scope.aggChartIsLoading = false;
          });
      }

      function updateStorage () {
        // Save axis and cycle selections
        localStorage.setItem(localStorageXAxisKey, JSON.stringify($scope.xAxisSelectedItem));
        localStorage.setItem(localStorageYAxisKey, JSON.stringify($scope.yAxisSelectedItem));

        localStorage.setItem(localStorageFromCycleKey, JSON.stringify($scope.fromCycle.selected_cycle));
        localStorage.setItem(localStorageToCycleKey, JSON.stringify($scope.toCycle.selected_cycle));
      };

      /*  Generate an array of color objects to be used as part of chart configuration
       Each color object should have the following properties:
       {
       seriesName:  A string value for the name of the series
       color:       A hex value for the color
       }
       A side effect of this method is that the colors are also applied to the propertyCounts object
       so that they're available in the table view beneath the chart that lists group details.
       */
      function mapColors (propertyCounts) {
        if (!propertyCounts) return [];
        var colorsArr = [];
        var numPropertyGroups = propertyCounts.length;
        for (var groupIndex = 0; groupIndex < numPropertyGroups; groupIndex++) {
          var obj = {
            color: $scope.defaultColors[groupIndex],
            seriesName: propertyCounts[groupIndex].yr_e
          };
          propertyCounts[groupIndex].color = obj.color;
          colorsArr.push(obj);
        }
        //propertyCounts.reverse(); //so the table/legend order matches the order Dimple will build the groups
        return colorsArr;
      }

      var localStorageFromCycleKey = base_storage_key + '.fromcycle';
      var localStorageToCycleKey = base_storage_key + '.tocycle';

      /* Call the update method so the page initializes
       with the values set in the scope */
      function init () {

        // Initialize pulldowns
        $scope.fromCycle = {
          selected_cycle: JSON.parse(localStorage.getItem(localStorageFromCycleKey)) || _.head($scope.cycles)
        };
        $scope.toCycle = {
          selected_cycle: JSON.parse(localStorage.getItem(localStorageToCycleKey)) || _.last($scope.cycles)
        };

        // Attempt to load selections
        $scope.updateChartData();
      }

      init();


    }]);
