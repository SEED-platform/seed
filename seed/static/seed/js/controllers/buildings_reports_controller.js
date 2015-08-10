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


    $scope.items = [
      {name:"Gross Floor Area", varName:"gross_floor_area", value:0},
      {name:"Building Classification", varName:"use_description", value:1},
      {name:"Year Built", varName:"year_built", value:2}
    ]

    $scope.selectedItem = $scope.items[0];
    
    $scope.chart1Data = [
      /*
      {x: 0, gross_floor_area: 4, use_description: 14, year_built:1970},
      {x: 1, gross_floor_area: 8, use_description: 1, year_built:1980},
      {x: 2, gross_floor_area: 15, use_description: 11, year_built:1960},
      {x: 3, gross_floor_area: 16, use_description: 147, year_built:1970},
      {x: 4, gross_floor_area: 23, use_description: 87, year_built:1980},
      {x: 5, gross_floor_area: 42, use_description: 45, year_built:1940}
      */
    ];

    $scope.chart1Options = {
      series: [
        {
          y: "gross_floor_area",
          label: " ",
          color: "#2ca02c",
          type: "column"
        }
      ]
    }
   
   $scope.updateChart1 = function(){
    var yAxisVar = $scope.selectedItem.varName;
    $scope.chart1Options.series[0].y = yAxisVar;
   }

  function init(){
    buildings_reports_service.get_report_data().then(function(data) {
      // resolve promise
      $scope.chart1Data = data;
    });
  }



  init();

    
}]);
