angular.module('basicBuildingInfoChart', [])
.directive('basicBuildingInfoChart', ['$window', function ($window) {
  return {
    restrict: 'E',
    replace: true,
    scope: {
            onchartrendered: '&',
            data: '=',
            chartType: '@',
            height: '@'
    },
    require: ['basicBuildingInfoChart'],
    link: function (scope, element, attrs, controllers) {
      
      var graphController = controllers[0];

      //init the chart
      graphController.setChartType(scope.chartType);
      graphController.createChartSVG();
      graphController.createChart();
      graphController.createChartAxes();

      /*
        The 'data' object should have the following properties:

          series :      a string value indicating what the series for the dimple chart will be
          graphData :   an array of objects to serve as actual chart data
          xAxisTitle :  a string value for the x axis title
          yAxisTitle :  a string value for the y axis title

      */
      scope.$watch('data', function(newValue) {

        //If the new value is empty or has properties but 'chartData' is empty, just clear the chart and return
        if (newValue===undefined || newValue.length === 0 || (newValue.chartData && newValue.chartData.length === 0)){
          graphController.clearChart();
          return;
        }

        if (newValue && newValue.chartData) {
          
          graphController.setYAxisType(newValue.yAxisType);
          graphController.clearChart();
          graphController.createChart();
          graphController.createChartAxes(newValue.xAxisTickFormat, newValue.yAxisTickFormat);  
          graphController.createChartLegend();      

          graphController.updateChart(  newValue.chartData, 
                                        newValue.series, 
                                        newValue.xAxisTitle, 
                                        newValue.yAxisTitle,
                                        newValue.yAxisMin);
          scope.onchartrendered();
        }
      });

      angular.element($window).bind('resize', function() {
          graphController.resizeChart();  
      });

    },
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
      
      var id;
      var svg;
      var chart;
      var xAxis;
      var yAxis;
      var legend;
      var autoresize = false;
      var yAxisType = "Measure";
      var hasData = false;
      var chartType = "";

      //TODO: Read in width and height from directive 
      var width = "100%";
      var height= $scope.height;

      autoresize = true;
      

      this.createChartSVG = function () {

        var id = (Math.random() * 1e9).toString(36).replace(".", "_");
        $element.append('<div class="dimple-graph" id="dng-'+ id +'"></div>'); 

        // create an svg element
        svg = dimple.newSvg('#dng-'+ id +'', width, height);       
      }

      this.createChart = function (){ 
        // create the dimple chart using the d3 selection of our <svg> element
        chart = new dimple.chart(svg, []);   
        if (yAxisType=="Category"){
           chart.setMargins(150, 60, 60, 40);
        } else {
           chart.setMargins(90, 60, 60, 40);
        }
       
        chart.noFormats = false; //use autostyle
        chart.draw(0);
      }

      this.createChartAxes = function (xAxisTickFormat, yAxisTickFormat){
        if (!xAxisTickFormat){
          xAxisTickFormat = ",.0f"
        }
        if (!yAxisTickFormat){
          yAxisTickFormat = ",.0f"
        }

        xAxis = chart.addMeasureAxis('x', 'x');
        xAxis.tickFormat = xAxisTickFormat;

        if (yAxisType=="Measure"){
          yAxis = chart.addMeasureAxis('y', 'y');
          yAxis.tickFormat = yAxisTickFormat;
        } else {
          yAxis = chart.addCategoryAxis('y', 'y');
        }


      }

      this.createChartLegend = function (){
        legend = chart.addLegend(200, 10, 360, 20, "right");
      }      


      this.clearChart = function() {
        if (chart && chart.svg && hasData){
          chart.svg.selectAll('*').remove();
          hasData = false;
        }        
      }

      this.updateChart = function(chartData, series, xAxisTitle, yAxisTitle, yAxisMin){
        
        if (chart.series && chart.series.length>0 ){
          chart.series[0].shapes.remove();
          chart.series.splice(0, 1);
        }
        if (chartType=="bar"){
          chart.addSeries(series, dimple.plot.bar);
        } else {
          chart.addSeries(series, dimple.plot.bubble);
        }
        
        chart.data = chartData;
        hasData = chart.data && chart.data.length > 0;
        xAxis.title = xAxisTitle;
        yAxis.title = yAxisTitle;
        if (yAxisMin){
          yAxis.overrideMin = yAxisMin;
        }
        chart.draw(0);
      }

      this.setChartType = function(chType){
        chartType = chType;
      }

      this.resizeChart = function (){
        if (chart){
          chart.draw(0, true);
        }   
      }

      this.getYAxisType = function() {
        return yAxisType;
      };

      this.setYAxisType = function(value) {
        yAxisType = value;
      };
   

      this.getChart = function () {
        return chart;
      };

      this.draw = function () {
        chart.draw();
      };

      this.getID = function () {
        return id;
      };

     

    }]
  };
}]);







