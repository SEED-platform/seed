angular.module('angular-dimple.graph', [])

.directive('graph', ['$window', function ($window) {
  return {
    restrict: 'E',
    replace: true,
    scope: {
      onchartrendered: '&',
      data: '=',
      series: "=",
      yaxislabel: '@'
    },
    require: ['graph'],
    transclude: true,
    link: function (scope, element, attrs, controllers, transclude) {
      var graphController = controllers[0];
      graphController._createChart();
      scope.dataReady = false;
      scope.filters = [];

      var chart = graphController.getChart();
      var transition;
      if (attrs.transition) {
        transition = attrs.transition;
      } else {
        transition = 750;
      }

      scope.$watch('series', function(newValue) {
        scatterPlot = chart.addSeries(newValue, dimple.plot.bubble);
        scatterPlot.aggregate = dimple.aggregateMethod.avg;
      });

      scope.$watch('data', function(newValue) {
        if (newValue) {
          scope.dataReady = true;
          graphController.setData();
          chart.draw(transition);
          if (chart.data && chart.data.length>0) scope.onchartrendered();
        }
      });

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addScatterPlot();
        }
      });

      transclude(scope, function(clone){
        element.append(clone);
      });

      scope.onResize = function() {
        if (graphController.getAutoresize()){
          var chart = graphController.getChart();
          if (chart){
            chart.draw(0, true);
            if (chart.data && chart.data.length>0) scope.onchartrendered();
          }   
        }             
      }


      scope.$watch('yaxislabel', function(value){
        chart.axes[1].title=value;
      });

      angular.element($window).bind('resize', function() {
          scope.onResize(); 
      });

    },
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
      var chart;
      var autoresize = false;
      var id = (Math.random() * 1e9).toString(36).replace(".", "_");
      $element.append('<div class="dimple-graph" id="dng-'+ id +'"></div>');     

      this._createChart = function () {
        // create an svg element

        var width = $attrs.width ? $attrs.width : '100%';
        var height = $attrs.height ? $attrs.height : '100%';
        autoresize = $attrs.autoresize ? $attrs.autoresize.toLowerCase()==='true' : false;

        var svg = dimple.newSvg('#dng-'+ id +'', width, height);
        var data = $scope.data;

        // create the dimple chart using the d3 selection of our <svg> element
        chart = new dimple.chart(svg, data);

        if ($attrs.margin) {
          chart.setMargins($attrs.margin);
        } else {
          chart.setMargins(60, 60, 20, 40);
        }

        // auto style
        var autoStyle = $attrs.autoStyle === 'false' ? true : false;
        chart.noFormats = autoStyle;

        // Apply palette styles
        if ($attrs.color) {
          var palette = $scope.color;
          for (var i = 0; i < palette.length; i++ ) {
            chart.assignColor(palette[i].name, palette[i].fill, palette[i].stroke, palette[i].opacity);
          }
        }
      };

      this.addScatterPlot = function() {
        scatterPlot = chart.addSeries($scope.series, dimple.plot.bubble);
        scatterPlot.aggregate = dimple.aggregateMethod.avg;
        graphController.filter($attrs);
        graphController.draw();
      }

      this.getAutoresize = function (){
        return autoresize;
      }

      this.getChart = function () {
        return chart;
      };

      this.setData = function () {
        chart.data = $scope.data;
      };

      this.draw = function () {
        chart.draw();
      };

      this.getID = function () {
        return id;
      };

      this.filter = function (attrs) {
        if (attrs.value !== undefined) {
          $scope.filters.push(attrs.value);
        }
        if ($scope.filters.length) {
          chart.data = dimple.filterData($scope.data, attrs.field, $scope.filters);
        }

        if (attrs.filter !== undefined) {
          console.log("i see a filter");
          var thisFilter = attrs.filter.split(':');
          var field = thisFilter[0];
          var value = [thisFilter[1]];
          chart.data = dimple.filterData($scope.data, field, value);
        }
      };

    }]
  };
}]);