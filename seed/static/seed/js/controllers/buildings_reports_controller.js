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

  var ENERGY_STAR_VAR = "es_score";
  var EUI_VAR = "eui";


  $scope.esChartVars = [
    {name:"Gross Floor Area", varName:"gross_floor_area", value:0},
    {name:"Building Classification", varName:"use_description", value:1},
    {name:"Year Built", varName:"year_built", value:2}
  ]

  $scope.euiChartVars = [
    {name:"Gross Floor Area", varName:"gross_floor_area", value:0},
    {name:"Building Classification", varName:"use_description", value:1},
    {name:"Year Built", varName:"year_built", value:2}
  ]

  $scope.esChartSelectedVar = $scope.esChartVars[0];
  $scope.euiChartSelectedVar = $scope.euiChartVars[0];
  
  $scope.esChartData = [];
  $scope.euiChartData = [];

  $scope.esChartOptions = {      
    axes: {
      x: {key: ENERGY_STAR_VAR}
    },
    series: [
      {
        y: $scope.esChartSelectedVar.varName,
        label: " ",
        color: "#2ca02c",
        type: "column"
      }
    ]
  }

  $scope.euiChartOptions = {      
    axes: {
      x: {key: EUI_VAR}
    },
    series: [
      {
        y: $scope.euiChartSelectedVar.varName,
        label: " ",
        color: "#2ca02c",
        type: "column"
      }
    ]
  }

   
  $scope.updateESChart = function(selectedVar){
    var yVar = selectedVar.varName;
    getESChartData(yVar);
  }

  function getESChartData(yVar){
    buildings_reports_service.get_report_data(ENERGY_STAR_VAR, yVar).then(function(data) {
      // resolve promise
      $scope.esChartData = data;
      // update chart
      $scope.esChartOptions.series[0].y = yVar;
    });
  }

  $scope.updateEUIChart = function(selectedVar){
    var yVar = selectedVar.varName;
    getEUIChartData(yVar);
  }

  function getEUIChartData(yVar){
    buildings_reports_service.get_report_data(EUI_VAR, yVar).then(function(data) {
      // resolve promise
      $scope.euiChartData = data;
      // update chart
      $scope.euiChartOptions.series[0].y = yVar;
    });
  }

  function init(){
    getESChartData($scope.esChartSelectedVar.varName)
    getEUIChartData($scope.euiChartSelectedVar.varName)
  }

  init();
    
}]);
