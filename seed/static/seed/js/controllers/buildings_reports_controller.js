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

  var EUI_X_AXIS_LABEL = "Energy Use Intensity";
  var ES_X_AXIS_LABEL = "Energy Star Score";

  //the following variable keeps track of which
  //series will be sent to the graphs when data is updated
  //('series' values are used by the dimple graphs to group data)
  $scope.euiChartSeries = ["id", "yr_e"];
  $scope.euiAggChartSeries = ["use_description", "yr_e"];



  /* DATEPICKERS */

  $scope.startDate = new Date();
  $scope.startDatePickerOpen = false;
  $scope.endDate = new Date();
  $scope.endDatePickerOpen = false;

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


  /* FILTER SUBMIT */
  
  $scope.updateFilters = function ($event) {        
    //Dates are already current so don't need to update them here.
    clearSummaryFields();    
    getSummaryData();
    getChartData();
  }

  function getChartData(){
    getESChartData();
    getEUIChartData();
  }


  /* SUMMARY DATA */
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


  /* GRAPHS */

  var ENERGY_STAR_VAR = "energy_score";
  var EUI_VAR = "site_eui";

  $scope.esChartVars = [
    { 
      name:"Gross Floor Area", 
      varName:"gross_floor_area",
      yAxisLabel:"Gross Floor Area (ft2)",
      xAxisTickFormat: ",.0f",
      yAxisTickFormat: ",.0f",
      yAxisMin: ""
    },
    { 
      name:"Building Classification",  
      varName:"use_description",
      yAxisLabel:"Building Classification",
      xAxisTickFormat: ",.0f",
      yAxisTickFormat: "",
      yAxisMin: ""
    },
    { 
      name:"Year Built", 
      varName:"year_built",
      yAxisLabel:"Year Built",
      xAxisTickFormat: ",.0f",
      yAxisTickFormat: "d",
      yAxisMin: "1900"
    }
  ];


  $scope.euiChartVars = [
    { 
      name:"Gross Floor Area", 
      varName:"gross_floor_area", 
      yAxisLabel:"Gross Floor Area (Thousand ft2)",
      xAxisTickFormat: ",.0f",
      yAxisTickFormat: ",.0f",
      yAxisMin: ""
    },
    {
      name:"Building Classification", 
      varName:"use_description", 
      yAxisLabel:"Building Classification",
      xAxisTickFormat: ",.0f",
      yAxisTickFormat: "",
      yAxisMin: ""
    },
    {
      name:"Year Built", 
      varName:"year_built", 
      yAxisLabel:"Year Built",
      xAxisTickFormat: ",.0f",
      yAxisTickFormat: "d",
      yAxisMin: "1900"
    }
  ]

  $scope.esChartIsLoading = true;
  $scope.euiChartIsLoading = true;

  $scope.esChartSelectedVar = $scope.esChartVars[0];
  $scope.esChartYAxisLabel = $scope.esChartSelectedVar.yAxisLabel;
  $scope.esChartData = [];

  $scope.euiChartSelectedVar = $scope.euiChartVars[0];
  $scope.euiChartYAxisLabel = $scope.euiChartSelectedVar.yAxisLabel;  
  $scope.euiChartData = [];

  $scope.updateESChart = function(selectedVar){
    $scope.esChartSelectedVar = selectedVar;
    $scope.esChartYAxisLabel = selectedVar.yAxisLabel;
    getESChartData();
    getESChartAggData();
  }

  function getESChartData(){
    
  }

  function getESChartAggData(){

  }

  $scope.updateEUICharts = function(selectedVar){
    $scope.euiChartSelectedVar = selectedVar;
    $scope.euiChartYAxisLabel = selectedVar.yAxisLabel;
    getEUIChartData();
    getEUIChartAggData();
  }

  function getEUIChartData(){    
    var yVar = $scope.euiChartSelectedVar.varName;
    $scope.euiChartIsLoading = true;
    buildings_reports_service.get_report_data(EUI_VAR, yVar, $scope.startDate, $scope.endDate)
      .then(function(data) {    

        var yAxisType = ( yVar === 'use_description' ? 'Category' : 'Measure');

        $scope.euiChartData = {
          "series":  $scope.euiChartSeries,
          "chartData": data,
          "xAxisTitle": EUI_X_AXIS_LABEL,
          "yAxisTitle": $scope.euiChartYAxisLabel,
          "yAxisType": yAxisType,
          "yAxisMin" : $scope.euiChartSelectedVar.yAxisMin,          
          "xAxisTickFormat": $scope.euiChartSelectedVar.xAxisTickFormat,
          "yAxisTickFormat": $scope.euiChartSelectedVar.yAxisTickFormat
        }
      });
  }

  function getEUIChartAggData(){
    var yVar = $scope.euiChartSelectedVar.varName;
    $scope.euiAggChartIsLoading = true;
    buildings_reports_service.get_aggregated_report_data(EUI_VAR, yVar, $scope.startDate, $scope.endDate)
      .then(function(data) {    
        $scope.euiAggChartData = {
          "series":  $scope.euiAggChartSeries,
          "chartData": data,
          "yAxisType": "Category",
          "xAxisTitle": EUI_X_AXIS_LABEL,
          "yAxisTitle": $scope.euiChartYAxisLabel
        }
      });

  }


  $scope.esChartRendered = function(){
    $scope.esChartIsLoading = false;     
  }

  $scope.euiChartRendered = function(){
    $scope.euiChartIsLoading = false;     
  }

  $scope.euiAggChartRendered = function(){
    $scope.euiAggChartIsLoading = false;
  }

  function clearGraphs() {
    //TODO : IMPLEMENT
  } 

  function init(){
    $scope.updateEUICharts($scope.euiChartSelectedVar);
  }

  init();

    
}]);
