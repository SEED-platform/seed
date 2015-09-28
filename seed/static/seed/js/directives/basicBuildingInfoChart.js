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

      /*
        The 'data' object should have the following properties. 

          series :          A string value indicating what the series for the dimple chart will be
          chartData :       An array of objects to serve as actual chart data
          xAxisTitle :      A string value for the x axis title
          yAxisTitle :      A string value for the y axis title          
          yAxisType:        A string value indiciating the type of axis (Dimple value, e.g. 'Measure')
          yAxisMin:         An integer value for the minimum value on the y axis
          xAxisTickFormat:  A string value for the y axis tick format  (Dimple value)
          yAxisTickFormat:  A string value for the y axis tick format  (Dimple value)
          colors :          An array of objects that defines the colors for the series.
                            Each object with the following properties:
                                "seriesName"  : A string value for the series name
                                "color"       : A hexidecimal string for the color for this series

      */
      scope.$watch('data', function(newValue) {

        //If the new value is empty or has properties but 'chartData' is empty, just clear the chart and return
        if (newValue===undefined || newValue.length === 0 || (newValue.chartData && newValue.chartData.length === 0)){
          graphController.clearChart();
          return;
        }

        if (newValue && newValue.chartData) {          
          graphController.setYAxisType(newValue.yAxisType);
          graphController.updateChart(  newValue.series, 
                                        newValue.chartData,                                        
                                        newValue.xAxisTitle, 
                                        newValue.yAxisTitle,
                                        newValue.yAxisType, 
                                        newValue.yAxisMin,
                                        newValue.xAxisTickFormat,
                                        newValue.yAxisTickFormat,
                                        newValue.colors);
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
      var self = this;
      var truncateLength = 15;

      var defaultColors = [
          new dimple.color("#458cc8"),
          new dimple.color("#c83737"),
          new dimple.color("#1159a3"),
          new dimple.color("#f2c41d"),
          new dimple.color("#939495"),
      ]; 

      var width = "100%";
      var height= $scope.height;
      autoresize = true;      

      /* Create the <div> that holds the svg and the svg itself.
         This method should only be called once. */
      this.createChartSVG = function () {
        var id = (Math.random() * 1e9).toString(36).replace(".", "_");
        $element.append('<div class="dimple-graph" id="dng-'+ id +'"></div>'); 

        // create an svg element
        var svgID = '#dng-'+ id +'';
        svg = dimple.newSvg(svgID, width, height);     
      }

      /*  Define the Dimple chart and load data based on the configuration and data arguments passed in. 
          We do a complete recreation of the chart each time this method is called.  */ 
      this.updateChart = function(series, chartData, xAxisTitle, yAxisTitle, yAxisType, yAxisMin, xAxisTickFormat, yAxisTickFormat, colors){

        self.clearChart();
        self.createChart();
        self.createChartAxes(yAxisType, yAxisMin, xAxisTickFormat, yAxisTickFormat);
       
        //setup colors
        if (colors && colors.length>0){
          var newColors = [];
          var numColors = colors.length;
          for (var index = 0; index<numColors; index++){
            var obj = colors[index];
            chart.assignColor(obj.seriesName, obj.color, obj.color, 1);
          }
        } else {
          chart.defaultColors = defaultColors;
        }

        //set type of chart and the series it will use to group data
        if (chartType=="bar"){
          var s = chart.addSeries(series, dimple.plot.bar);
        } else {
          var s = chart.addSeries(series, dimple.plot.bubble);
        }
        s.getTooltipText = function(e){
          var arr = [];
          var yLabel = 
          arr.push("Year Ending : " + e.aggField[1]);
          arr.push( yAxisTitle + " : " + e.cy.toString());
          arr.push( xAxisTitle +" : " + e.cx.toString());
          return arr;
        }
        
        //attach data and titles and redraw
        chart.data = chartData;
        hasData = chart.data && chart.data.length > 0;
        xAxis.title = xAxisTitle;
        yAxis.title = yAxisTitle;
        if (yAxisMin){
          yAxis.overrideMin = yAxisMin;
        }

        chart.draw(0);    

      }

      /*  Create the Dimple chart, attaching it to pre-existing svg element.
          This method can be called each time we need a complete refresh.  */
      this.createChart = function (){ 
        // create the dimple chart using the d3 selection of our <svg> element
        chart = new dimple.chart(svg, []); 
        chart.defaultColors = defaultColors;  
        chart.setMargins(120, 20, 60, 40);
       
        chart.noFormats = false; //use autostyle
        chart.draw(0);
      }

      /* Create the axes for the chart, using value passed in from external controller. */
      this.createChartAxes = function (yAxisType, yAxisMin, xAxisTickFormat, yAxisTickFormat){
        
        if (!xAxisTickFormat){
          xAxisTickFormat = ",.0f"
        }       

        xAxis = chart.addMeasureAxis('x', 'x');
        xAxis.tickFormat = xAxisTickFormat;
     
        if (yAxisType=="Measure"){
          if (!yAxisTickFormat){
            yAxisTickFormat = ",.0f"
          }
          yAxis = chart.addMeasureAxis('y', 'y');
          yAxis.tickFormat = yAxisTickFormat;
        } else {
          yAxis = chart.addCategoryAxis('y', ['y','yr_e']);
          yAxis.addOrderRule("y", false);     
          yAxis._getFormat = function() { return my_custom_format; };
        }
      }

      function my_custom_format(value) {
          if (value && value.length>truncateLength){
            return value.substring(0,truncateLength) + "...";
          }
          return value;
      }

      this.createChartLegend = function (){
        legend = chart.addLegend(200, 10, 360, 20, "right bottom");
      }      

      this.clearChart = function() {
        if (chart && chart.svg && hasData){
          chart.svg.selectAll('*').remove();
          hasData = false;
        }        
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







