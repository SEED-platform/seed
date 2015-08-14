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

  var ENERGY_STAR_VAR = "energy_score";
  var EUI_VAR = "site_eui";


  $scope.esChartVars = [
    { 
      name:"Gross Floor Area", 
      varName:"gross_floor_area",
      yAxisLabel:"Gross Floor Area (Thousand ft2)"
    },
    { 
      name:"Building Classification",  
      varName:"use_description",
      yAxisLabel:"Building Classification"
    },
    { 
      name:"Year Built", 
      varName:"year_built",
      yAxisLabel:"Year Built"
    }
  ]

  $scope.euiChartVars = [
    {name:"Gross Floor Area", varName:"gross_floor_area", value:0},
    {name:"Building Classification", varName:"use_description", value:1},
    {name:"Year Built", varName:"year_built", value:2}
  ]

  $scope.esChartSelectedVar = $scope.esChartVars[0];
  $scope.euiChartSelectedVar = $scope.euiChartVars[0];
  $scope.esChartYAxisLabel = $scope.euiChartSelectedVar.yAxisLabel;
  
  $scope.esChartData = [];
  $scope.euiChartData = [];

   
  $scope.updateESChart = function(selectedVar){
    var yVar = selectedVar.varName;
    $scope.esChartYAxisLabel = selectedVar.yAxisLabel;
    getESChartData(yVar);
  }

  function getESChartData(yVar){
    buildings_reports_service.get_report_data(ENERGY_STAR_VAR, yVar).then(function(data) {
      // resolve promise      
      $scope.esChartData = data;
    });
  }

  $scope.updateEUIChart = function(selectedVar){
    var yVar = selectedVar.varName;
    $scope.euiChartYAxisLabel = selectedVar.yAxisLabel;
    getEUIChartData(yVar);
  }

  function getEUIChartData(yVar){
    buildings_reports_service.get_report_data(EUI_VAR, yVar).then(function(data) {
      // resolve promise
      $scope.euiChartData = data;
    });
  }

  function getSummaryData() {
    buildings_reports_service.get_summary_data().then(function(data) {
      // resolve promise
      $scope.summaryData = data;
    });
  }

  function init(){
    $scope.updateESChart($scope.esChartSelectedVar);
    $scope.updateEUIChart($scope.euiChartSelectedVar);
    getSummaryData();
  }

  init();
    
}]);
