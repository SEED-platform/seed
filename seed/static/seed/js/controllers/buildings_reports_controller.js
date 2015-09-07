/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.buildings_reports', [])
.controller('buildings_reports_controller', [ '$scope',
                                              '$log',
                                              '$modal',
                                              'buildings_reports_service',
                                    function( $scope,
                                              $log,
                                              $modal,
                                              buildings_reports_service
                                            ) {


  'use strict';

  /* SCOPE VARS */

  // Chart variables : 
  // these next two arrays define the various properties 
  // of the variables the user can select for graphing.            
  $scope.xAxisVars = [
    { 
      name: "Site EUI",
      label: "Site Energy Use Intensity", 
      varName: "site_eui",
      axisLabel: "Site EUI (kBtu/ft2)",
      axisType: "Measure",
      axisTickFormat: ",.0f"
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
  $scope.startDate = new Date();
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
  $scope.chartIsLoading = true;
  $scope.aggChartIsLoading = true;


  /* UI HANDLERS */

  // Datepicker updates 

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


  /* AXIS VARIABLE PICKERS SUBMIT */
  
  $scope.updateChartData = function(){
    clearChartData();   
    getChartData();
    getAggChartData();
    updateTitles();
  }

  function clearChartData(){
    $scope.chartData = [];
    $scope.aggChartData = [];
  }

  function updateTitles(){
    $scope.chart1Title = $scope.xAxisSelectedItem.label + " vs. " + $scope.yAxisSelectedItem.label;
    $scope.chart2Title = $scope.xAxisSelectedItem.label + " vs. " + $scope.yAxisSelectedItem.label;
  }

 


  /* SUMMARY DATA */
  /*
  function getSummaryData() {
    buildings_reports_service.get_summary_data().then(function(data) {
      // resolve promise
      $scope.summaryData = data;
    });
  }

  function clearSummaryFields() {
    initSummaryFields();
  }
  
  function initSummaryFields() {
    $scope.summaryData = {
                            num_buildings: "", 
                            avg_eui: "",
                            avg_energy_score: ""
                          };
  }
  initSummaryFields();
  */

 

  

  function getChartData(){    

    var xVar = $scope.xAxisSelectedItem.varName;
    var yVar = $scope.yAxisSelectedItem.varName;
    $scope.chartIsLoading = true;

    buildings_reports_service.get_report_data(xVar, yVar, $scope.startDate, $scope.endDate)
      .then(function(data) {    
        var yAxisType = ( yVar === 'use_description' ? 'Category' : 'Measure');
        $scope.chartData = {
          "series":  $scope.chartSeries,
          "chartData": data,
          "xAxisTitle": $scope.xAxisSelectedItem.axisLabel,
          "yAxisTitle": $scope.yAxisSelectedItem.axisLabel,
          "yAxisType": $scope.yAxisSelectedItem.axisType,
          "yAxisMin" : $scope.yAxisSelectedItem.axisMin,          
          "xAxisTickFormat": $scope.xAxisSelectedItem.axisTickFormat,
          "yAxisTickFormat": $scope.yAxisSelectedItem.axisTickFormat
        }
      });
  }

  function getAggChartData(){

    var xVar = $scope.xAxisSelectedItem.varName;
    var yVar = $scope.yAxisSelectedItem.varName;
    $scope.aggChartIsLoading = true;

    buildings_reports_service.get_aggregated_report_data(xVar, yVar, $scope.startDate, $scope.endDate)
      .then(function(data) {    
        $scope.aggChartData = {
          "series":  $scope.aggChartSeries,
          "chartData": data,
          "xAxisTitle": $scope.xAxisSelectedItem.axisLabel,
          "yAxisTitle": $scope.yAxisSelectedItem.axisLabel,
          "yAxisType": "Category"
        }
      });

  }


  $scope.chartRendered = function(){
    $scope.chartIsLoading = false;     
  }

  $scope.aggChartRendered = function(){
    $scope.aggChartIsLoading = false;
  }

  function clearGraphs() {
    //TODO : IMPLEMENT
  } 

  function init(){
    $scope.updateChartData();
  }

  init();

    
}]);
