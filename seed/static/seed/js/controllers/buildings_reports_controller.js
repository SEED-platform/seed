/**
  This controller handles the building reports page, watching for and remembering
  the user's selections for chart parameters like date range and x and y variables,
  and then updating the chart directies when the user clicks the update chart button.
*/

angular.module('BE.seed.controller.buildings_reports', [])
.controller('buildings_reports_controller', [ '$scope',
                                              '$log',
                                              'buildings_reports_service',
                                    function( $scope,
                                              $log,
                                              buildings_reports_service
                                            ){


  'use strict';

  /* Define the first five colors. After that, rely on Dimple's default colors. */
  $scope.defaultColors = ["#c83737","#458cc8","#1159a3","#f2c41d","#939495"];

  /* SCOPE VARS */
  /* ~~~~~~~~~~ */

  /** Chart variables : 
      these next two arrays, $scope.xAxisVars and $scope.yAxisVars, define the various properties 
      of the variables the user can select for graphing.

      Each object contains information used by the dropdown controls as well as information
      used to customize the chart specifically for that value (e.g. axisTickFormat)

      Ideally, if we need to add new variables, we should just be able to add a new object to 
      either of these arrays. (However, at first when adding new variables we might need to add
      new functionality to the directive to handle any idiosyncracies of graphing that new variable.)
  */           
  $scope.xAxisVars = [
    { 
      name: "Site EUI",                     //short name for variable, used in pulldown
      label: "Site Energy Use Intensity",   //full name for variable
      varName: "site_eui",                  //name of variable, to be sent to server
      axisLabel: "Site EUI (kBtu/ft2)",     //label to be used in charts, should include units
      axisType: "Measure",                  //DimpleJS property for axis type
      axisTickFormat: ",.0f"                //DimpleJS property for axis tick format
    },    
    {       
      name: "Source EUI",
      label: "Source Energy Use Intensity", 
      varName: "source_eui",
      axisLabel: "Source EUI (kBtu/ft2)",
      axisType: "Measure",
      axisTickFormat: ",.0f"
    },
    { 
      name: "Weather Norm. Site EUI",
      label: "Weather Normalized Site Energy Use Intensity", 
      varName: "site_eui_weather_normalized",
      axisLabel: "Weather Normalized Site EUI (kBtu/ft2)",
      axisType: "Measure",
      axisTickFormat: ",.0f"
    },
    { 
      name: "Weather Norm. Source EUI",
      label: "Weather Normalized Source Energy Use Intensity", 
      varName: "source_eui_weather_normalized",
      axisLabel: "Weather Normalized Source EUI (kBtu/ft2)",
      axisType: "Measure",
      axisTickFormat: ",.0f"
    },
    { 
      name : "Energy Star Score",
      label: "Energy Star Score", 
      varName: "energy_score",
      axisLabel: "Energy Star Score",
      axisType: "Measure",
      axisTickFormat: ",.0f"
    }
  ];
  
  $scope.yAxisVars = [
    { 
      name: "Gross Floor Area",
      label:"Gross Floor Area", 
      varName:"gross_floor_area",
      axisLabel:"Gross Floor Area (ft2)",
      axisTickFormat: ",.0f",
      axisType: "Measure",
      axisMin: ""
    },
    { 
      name: "Building Classification",
      label:"Building Classification",  
      varName:"use_description",
      axisLabel:"Building Classification",
      axisTickFormat: "",
      axisType: "Category",
      axisMin: ""
    },
    { 
      name: "Year Built",
      label:"Year Built", 
      varName:"year_built",
      axisLabel:"Year Built",
      axisTickFormat: ".0f",
      axisType: "Measure",
      axisMin: "1900"
    }
  ];


  // Chart titles
  $scope.chart1Title = "";
  $scope.chart2Title = "";

  // Datepickers
  var initStartDate = new Date();
  initStartDate.setYear(initStartDate.getFullYear()-1);
  $scope.startDate = initStartDate;
  $scope.startDatePickerOpen = false;
  $scope.endDate = new Date();
  $scope.endDatePickerOpen = false;
  
  // Series
  // the following variable keeps track of which
  // series will be sent to the graphs when data is updated
  // ('series' values are used by the dimple graphs to group data)
  $scope.chartSeries = ["id","yr_e"];
  $scope.aggChartSeries = ["use_description", "yr_e"];

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
  $scope.chartStatusMessage = "No data";     
  $scope.aggChartStatusMessage = "No data";


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
  
  /* Update data used by the chart. This will force the charts to re-render*/
  $scope.updateChartData = function(){
    clearChartData();   
    $scope.chartStatusMessage = "Loading data...";
    $scope.aggChartStatusMessage = "Loading data...";
    getChartData();
    getAggChartData();
    updateChartTitles();    
  }


  /* FLAGS FOR CHART STATE */
  /* ~~~~~~~~~~~~~~~~~~~~~ */

  /* The directive will call this, so we can update our flag for the state of the chart. */
  $scope.chartRendered = function(){
    $scope.chartIsLoading = false;     
  }

  /* The directive will call this, so we can update our flag for the state of the chart. */
  $scope.aggChartRendered = function(){
    $scope.aggChartIsLoading = false;
  }


  /* PRIVATE FUNCTIONS (so to speak) */
  /* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

  /* Clear the data used by the chart*/
  function clearChartData(){
    $scope.chartData = [];
    $scope.aggChartData = [];
    $scope.buildingCounts = [];
    $scope.aggBuildingCounts = [];
  }

  /* Update the titles above each chart*/
  function updateChartTitles(){
    $scope.chart1Title = $scope.xAxisSelectedItem.label + " vs. " + $scope.yAxisSelectedItem.label;
    $scope.chart2Title = $scope.xAxisSelectedItem.label + " vs. " + $scope.yAxisSelectedItem.label + " (Aggregated)";
  }

  function setChartStatusMessages(chartData){
    if (chartData.chartData && chartData.chartData.length>0) {
      return ""
    } else {
      return "No Data";
    }
  }


   /** Get the 'raw' (unaggregated) chart data from the server for the scatter plot chart.
      The user's selections are already stored as proprties on the scope, so use 
      those for the parameters that need to be sent to the server.

      When chart data is returned from the service, pass it to our chart directive along 
      with configuration information. The chart will update automatically as it's watching the
      chartData property on the scope.

      In the future, if we want the chart to look or behave differently depending on the data,
      we can pass in different configuration options.
      The chart will update automatically as it's watching the chartData property on the scope.
  */  
  function getChartData(){    

    var xVar = $scope.xAxisSelectedItem.varName;
    var yVar = $scope.yAxisSelectedItem.varName;
    $scope.chartIsLoading = true;

    buildings_reports_service.get_report_data(xVar, yVar, $scope.startDate, $scope.endDate)
      .then(function(data) {    
          var yAxisType = ( yVar === 'use_description' ? 'Category' : 'Measure');
          var bldgCounts = data.building_counts;
          var colorsArr = mapColors(bldgCounts);
          $scope.buildingCounts = bldgCounts;
          $scope.chartData = {
            "series":  $scope.chartSeries,
            "chartData": data.chart_data,
            "xAxisTitle": $scope.xAxisSelectedItem.axisLabel,
            "yAxisTitle": $scope.yAxisSelectedItem.axisLabel,
            "yAxisType": $scope.yAxisSelectedItem.axisType,
            "yAxisMin" : $scope.yAxisSelectedItem.axisMin,          
            "xAxisTickFormat": $scope.xAxisSelectedItem.axisTickFormat,
            "yAxisTickFormat": $scope.yAxisSelectedItem.axisTickFormat,
            "colors": colorsArr
          } 
          if($scope.chartData.chartData && $scope.chartData.chartData.length > 0) {
            $scope.chartStatusMessage = "" 
          } else {
            $scope.chartStatusMessage = "No Data";  
          } 
        },
        function(data, status){
          $scope.chartStatusMessage = "Data load error."
          $log.error("#BuildingReportsController: Error loading chart data : " + status);
        })
      .finally(function(){
        $scope.chartIsLoading = false;
      })
  }

  /** Get the aggregated chart data from the server for the scatter plot chart.
      The user's selections are already stored as proprties on the scope, so use 
      those for the parameters that need to be sent to the server.

      When chart data is returned from the service, pass it to our chart directive along 
      with configuration information. The chart will update automatically as it's watching the
      chartData property on the scope.

      In the future, if we want the chart to look or behave differently depending on the data,
      we can pass in different configuration options.
      
  */  
  function getAggChartData(){

    var xVar = $scope.xAxisSelectedItem.varName;
    var yVar = $scope.yAxisSelectedItem.varName;
    $scope.aggChartIsLoading = true;
    buildings_reports_service.get_aggregated_report_data(xVar, yVar, $scope.startDate, $scope.endDate)
      .then(function(data) {    
          $scope.aggBuildingCounts = data.building_counts;
          var bldgCounts = data.building_counts;
          var colorsArr = mapColors(bldgCounts);
          $scope.aggBuildingCounts = bldgCounts;
          $scope.aggChartData = {
            "series":  $scope.aggChartSeries,
            "chartData": data.chart_data,
            "xAxisTitle": $scope.xAxisSelectedItem.axisLabel,
            "yAxisTitle": $scope.yAxisSelectedItem.axisLabel,
            "yAxisType": "Category",
            "colors": colorsArr
          }
          if($scope.aggChartData.chartData && $scope.aggChartData.chartData.length > 0) {
            $scope.aggChartStatusMessage = "" 
          } else {
            $scope.aggChartStatusMessage = "No Data";  
          }  
        },
        function(data, status){
          $scope.aggChartStatusMessage = "Data load error."
          $log.error("#BuildingReportsController: Error loading agg chart data : " + status);
        })
      .finally(function(){
        $scope.aggChartIsLoading = false;
      })
  }

  /*  Generate an array of color objects to be used as part of chart configuration
      Each color object should have the following properties:
        {
          seriesName:  A string value for the name of the series
          color:       A hex value for the color
        }   
      A side effect of this method is that the colors are also applied to the bldgCounts object
      so that they're available in the table view beneath the chart that lists group details. 
  */
  function mapColors(bldgCounts){    
    if (!bldgCounts) return [];
    var colorsArr = [];
    var numBldgGroups = bldgCounts.length;
    for (var groupIndex=0;groupIndex<numBldgGroups;groupIndex++){
      var obj = {};
      obj.seriesName = bldgCounts[groupIndex].yr_e;
      obj.color = $scope.defaultColors[groupIndex];
      bldgCounts[groupIndex].color = obj.color;
      colorsArr.push(obj);
    }
    //bldgCounts.reverse(); //so the table/legend order matches the order Dimple will build the groups
    return colorsArr;
  }

 
  /* Call the update method so the page initializes
     with the values set in the scope */
  function init(){
    //$scope.updateChartData();
  }

  init();

    
}]);
