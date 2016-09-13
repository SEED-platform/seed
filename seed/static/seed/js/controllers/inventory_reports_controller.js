/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
    'cycles',
    function ($scope,
              $log,
              $stateParams,
              inventory_reports_service,
              simple_modal_service,
              cycles) {

      $scope.inventory_type = $stateParams.inventory_type;

      /* Define the first five colors. After that, rely on Dimple's default colors. */
      $scope.defaultColors = ['#458cc8', '#779e1c', '#f2c41d', '#939495', '#c83737', '#f18630'];

      /* Setup models from "From" and "To" selectors */
      $scope.cycles = cycles;

      /* Model for pulldowns, initialized in init below */
      $scope.fromCycle = {};
      $scope.toCycle = {};

      /* SCOPE VARS */
      /* ~~~~~~~~~~ */

      /** Chart variables :
       these next two arrays, $scope.xAxisVars and $scope.yAxisVars, define the various properties
       of the variables the user can select for graphing.

       Each object contains information used by the dropdown controls as well as information
       used to customize the chart specifically for that value (e.g. axisTickFormat)

       Ideally, if we need to add new variables, we should just be able to add a new object to
       either of these arrays. (However, at first when adding new variables we might need to add
       new functionality to the directive to handle any idiosyncrasies of graphing that new variable.)
       */
      $scope.xAxisVars = [
        {
          name: 'Site EUI',                     //short name for variable, used in pulldown
          label: 'Site Energy Use Intensity',   //full name for variable
          varName: 'site_eui',                  //name of variable, to be sent to server
          axisLabel: 'Site EUI (kBtu/ft2)',     //label to be used in charts, should include units
          axisType: 'Measure',                  //DimpleJS property for axis type
          axisTickFormat: ',.0f'                //DimpleJS property for axis tick format
        }, {
          name: 'Source EUI',
          label: 'Source Energy Use Intensity',
          varName: 'source_eui',
          axisLabel: 'Source EUI (kBtu/ft2)',
          axisType: 'Measure',
          axisTickFormat: ',.0f'
        }, {
          name: 'Weather Norm. Site EUI',
          label: 'Weather Normalized Site Energy Use Intensity',
          varName: 'site_eui_weather_normalized',
          axisLabel: 'Weather Normalized Site EUI (kBtu/ft2)',
          axisType: 'Measure',
          axisTickFormat: ',.0f'
        }, {
          name: 'Weather Norm. Source EUI',
          label: 'Weather Normalized Source Energy Use Intensity',
          varName: 'source_eui_weather_normalized',
          axisLabel: 'Weather Normalized Source EUI (kBtu/ft2)',
          axisType: 'Measure',
          axisTickFormat: ',.0f'
        }, {
          name: 'Energy Star Score',
          label: 'Energy Star Score',
          varName: 'energy_score',
          axisLabel: 'Energy Star Score',
          axisType: 'Measure',
          axisTickFormat: ',.0f'
        }
      ];

      $scope.yAxisVars = [
        {
          name: 'Gross Floor Area',
          label: 'Gross Floor Area',
          varName: 'gross_floor_area',
          axisLabel: 'Gross Floor Area (ft2)',
          axisTickFormat: ',.0f',
          axisType: 'Measure',
          axisMin: ''
        }, {
          name: 'Property Classification',
          label: 'Property Classification',
          varName: 'use_description',
          axisLabel: 'Property Classification',
          axisTickFormat: '',
          axisType: 'Category',
          axisMin: ''
        }, {
          name: 'Year Built',
          label: 'Year Built',
          varName: 'year_built',
          axisLabel: 'Year Built',
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

      //Currently selected x and y variables
      $scope.xAxisSelectedItem = $scope.xAxisVars[0];  //initialize to first var
      $scope.yAxisSelectedItem = $scope.yAxisVars[0];  //initialize to first var

      //Chart data
      $scope.chartData = [];
      $scope.aggChartData = [];

      //Chart status
      $scope.chartIsLoading = false;
      $scope.aggChartIsLoading = false;

      //Setting the status messages will cause the small white status box to show above the chart
      //Setting these to empty string will remove that box
      $scope.chartStatusMessage = 'No data';
      $scope.aggChartStatusMessage = 'No data';


      /* UI HANDLERS */
      /* ~~~~~~~~~~~ */

      // Handle datepicker open/close events
      $scope.openStartDatePicker = function ($event) {
        console.debug('openStartDatePicker');
        $event.preventDefault();
        $event.stopPropagation();
        $scope.startDatePickerOpen = !$scope.startDatePickerOpen;
      };
      $scope.openEndDatePicker = function ($event) {
        console.debug('openEndDatePicker');
        $event.preventDefault();
        $event.stopPropagation();
        $scope.endDatePickerOpen = !$scope.endDatePickerOpen;
      };

      $scope.$watch('startDate', function (newval, oldval) {
        $scope.checkInvalidDate();
      });

      $scope.$watch('endDate', function (newval, oldval) {
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
      function clearChartData() {
        $scope.chartData = [];
        $scope.aggChartData = [];
        $scope.propertyCounts = [];
        $scope.aggPropertyCounts = [];
      }

      /* Update the titles above each chart*/
      function updateChartTitles() {
        $scope.chart1Title = $scope.xAxisSelectedItem.label + ' vs. ' + $scope.yAxisSelectedItem.label;
        $scope.chart2Title = $scope.xAxisSelectedItem.label + ' vs. ' + $scope.yAxisSelectedItem.label + ' (Aggregated)';
      }

      function setChartStatusMessages(chartData) {
        if (chartData.chartData && chartData.chartData.length > 0) {
          return '';
        } else {
          return 'No Data';
        }
      }


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
      function getChartData() {

        var xVar = $scope.xAxisSelectedItem.varName;
        var yVar = $scope.yAxisSelectedItem.varName;
        $scope.chartIsLoading = true;

        inventory_reports_service.get_report_data(xVar, yVar, $scope.toCycle.selected_cycle.start, $scope.fromCycle.selected_cycle.end)
          .then(function (data) {
              data = data.data;
              var yAxisType = ( yVar === 'use_description' ? 'Category' : 'Measure');
              var propertyCounts = data.property_counts;
              var colorsArr = mapColors(propertyCounts);
              $scope.propertyCounts = propertyCounts;
              $scope.chartData = {
                series: $scope.chartSeries,
                chartData: data.chart_data,
                xAxisTitle: $scope.xAxisSelectedItem.axisLabel,
                yAxisTitle: $scope.yAxisSelectedItem.axisLabel,
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
              $scope.chartStatusMessage = 'Data load error.';
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
      function getAggChartData() {

        var xVar = $scope.xAxisSelectedItem.varName;
        var yVar = $scope.yAxisSelectedItem.varName;
        $scope.aggChartIsLoading = true;
        inventory_reports_service.get_aggregated_report_data(
          xVar, yVar,
          $scope.toCycle.selected_cycle.start,
          $scope.fromCycle.selected_cycle.end
        ).then(function (data) {
            data = data.aggregated_data;
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
            if ($scope.aggChartData.chartData && $scope.aggChartData.chartData.length) {
              $scope.aggChartStatusMessage = '';
            } else {
              $scope.aggChartStatusMessage = 'No Data';
            }
          },
          function (data, status) {
            $scope.aggChartStatusMessage = 'Data load error.';
            $log.error('#InventoryReportsController: Error loading agg chart data : ' + status);
          })
          .finally(function () {
            $scope.aggChartIsLoading = false;
          });
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
        var colorsArr = [];
        var numPropertyGroups = propertyCounts.length;
        for (var groupIndex = 0; groupIndex < numPropertyGroups; groupIndex++) {
          var obj = {};
          obj.seriesName = propertyCounts[groupIndex].yr_e;
          obj.color = $scope.defaultColors[groupIndex];
          propertyCounts[groupIndex].color = obj.color;
          colorsArr.push(obj);
        }
        //propertyCounts.reverse(); //so the table/legend order matches the order Dimple will build the groups
        return colorsArr;
      }


      /* Call the update method so the page initializes
       with the values set in the scope */
      function init() {

        // Initialize pulldowns
        $scope.fromCycle = {
          selected_cycle: $scope.cycles.cycles[0]
        };
        $scope.toCycle = {
          selected_cycle: $scope.cycles.cycles[$scope.cycles.cycles.length - 1]
        };

      }

      init();


    }]);