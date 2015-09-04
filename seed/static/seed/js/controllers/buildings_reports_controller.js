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


  /* CONST */

  var EUI_AXIS_LABEL = "Energy Use Intensity";
  var EUI_UNITS = "ft2"
  var EUI_VAR_NAME = "site_eui";

  var ES_AXIS_LABEL = "Energy Star Score";
  var ES_VAR_NAME = "energy_score";


  /* SCOPE VARS */

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

  // Chart variables
  $scope.xAxisVars = [
    { 
      name: EUI_AXIS_LABEL, 
      varName: EUI_VAR_NAME,
      axisLabel: EUI_AXIS_LABEL + "(" + EUI_UNITS + ")",
      axisType: "Measure",
      axisTickFormat: ",.0f"
    },
    { 
      name: ES_AXIS_LABEL, 
      varName: ES_VAR_NAME,
      axisLabel: ES_AXIS_LABEL,
      axisType: "Measure",
      axisTickFormat: ",.0f"
    }
  ];
  
  $scope.yAxisVars = [
    { 
      name:"Gross Floor Area", 
      varName:"gross_floor_area",
      axisLabel:"Gross Floor Area (ft2)",
      axisTickFormat: ",.0f",
      axisType: "Measure",
      axisMin: ""
    },
    { 
      name:"Building Classification",  
      varName:"use_description",
      axisLabel:"Building Classification",
      axisTickFormat: "",
      axisType: "Category",
      axisMin: ""
    },
    { 
      name:"Year Built", 
      varName:"year_built",
      axisLabel:"Year Built",
      axisTickFormat: ".0f",
      axisType: "Measure",
      axisMin: "1900"
    }
  ];

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
  }

  function clearChartData(){
    $scope.chartData = [];
    $scope.aggChartData = [];
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
