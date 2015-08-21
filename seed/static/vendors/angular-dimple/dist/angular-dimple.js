/*! angular-dimple - 2.0.1 - 2015-08-21
*   https://github.com/esripdx/angular-dimple
*   Licensed ISC */
angular.module('angular-dimple', [
  'angular-dimple.graph',
  'angular-dimple.legend',
  'angular-dimple.x',
  'angular-dimple.y',
  'angular-dimple.r',
  'angular-dimple.line',
  'angular-dimple.bar',
  'angular-dimple.stacked-bar',
  'angular-dimple.area',
  'angular-dimple.stacked-area',
  'angular-dimple.scatter-plot',
  'angular-dimple.ring'
])

.constant('MODULE_VERSION', '0.0.1')

.value('defaults', {
  foo: 'bar'
});
angular.module('angular-dimple.area', [])

.directive('area', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['area', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var areaController = $controllers[0];
      var chart = graphController.getChart();

      function addArea () {
        if ($attrs.value) {
          area = chart.addSeries([$attrs.field], dimple.plot.area);
          graphController.filter($attrs);
          area.lineMarkers = true;
        } else {
          var values = dimple.getUniqueValues($scope.data, $attrs.field);
          angular.forEach(values, function(value){
            area = chart.addSeries([$attrs.field], dimple.plot.area);
            graphController.filter($attrs);
            area.lineMarkers = true;
          });
        }
        graphController.draw();
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addArea();
        }
      });
    }
  };
}]);


angular.module('angular-dimple.bar', [])

.directive('bar', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['bar', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var lineController = $controllers[0];
      var chart = graphController.getChart();

      function addBar () {
        var filteredData;
        bar = chart.addSeries([$attrs.field], dimple.plot.bar);
        graphController.filter($attrs);
        graphController.draw();
      }



      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addBar();
        }
      });
    }
  };
}]);
angular.module('angular-dimple.graph', [])

.directive('graph', ['$window', function ($window) {
  return {
    restrict: 'E',
    replace: true,
    scope: {
      onchartrendered: '&',
      data: '=',
      color: '=',
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

      scope.$watch('data', function(newValue) {
        if (newValue) {
          scope.dataReady = true;
          graphController.setData();
            chart.draw(transition);
            if (chart.data && chart.data.length>0) scope.onchartrendered();
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
angular.module('angular-dimple.legend', [])

.directive('graphLegend', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['graphLegend', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var chart = graphController.getChart();

      function addLegend () {
        var left = $attrs.left ? $attrs.left : "10%";
        var top = $attrs.top ? $attrs.top : "4%";
        var height = $attrs.height ? $attrs.height : "10%";
        var width = $attrs.width ? $attrs.width : "90%";
        var position = $attrs.position ? $attrs.position : 'left';
        chart.addLegend(left, top, width, height, position);
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addLegend();
        }
      });
    }
  };
}]);
angular.module('angular-dimple.line', [])

.directive('line', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['line', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var chart = graphController.getChart();
      var drawn = false;

      function addLine () {
        var filteredData;
        line = chart.addSeries([$attrs.field], dimple.plot.line);
        graphController.filter($attrs);
        line.lineMarkers = true;
        graphController.draw();
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addLine();
        }
      });

    }
  };
}]);
angular.module('angular-dimple.r', [])

.directive('r', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['r', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var chart = graphController.getChart();

      function addAxis () {
        r = chart.addMeasureAxis('p', $attrs.field);

        if ($attrs.title && $attrs.title !== "null") {
          r.title = $attrs.title;
        } else if ($attrs.title == "null") {
          r.title = null;
        }
      }

      $scope.$watch('data', function(newValue, oldValue) {
        if (newValue) {
          addAxis();
        }
      });
    }
  };
}]);
angular.module('angular-dimple.ring', [])

.directive('ring', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['ring', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var areaController = $controllers[0];
      var chart = graphController.getChart();

      function setData (data, series) {
        series.data = data;
      }

      function addRing () {
        var thickness;
        ring = chart.addSeries([$attrs.field], dimple.plot.pie);
        if ($attrs.thickness && !$attrs.diameter) {
          thickness = (100 - $attrs.thickness) + '%';
          ring.innerRadius = thickness;
        } else if ($attrs.thickness && $attrs.diameter) {
          thickness = ($attrs.diameter - $attrs.thickness) + '%';
          ring.innerRadius = thickness;
        } else {
          ring.innerRadius = "50%";
        }

        if ($attrs.diameter) {
          ring.outerRadius = ($attrs.diameter) + '%';
        }
        graphController.filter($attrs);
        graphController.draw();
      }

      $scope.$watch('data', function(newValue, oldValue) {
        if (newValue) {
          addRing();
        }
      });
    }
  };
}]);


angular.module('angular-dimple.scatter-plot', [])

.directive('scatterPlot', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['scatterPlot', '^graph'],
    controller: [function() {}],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var chart = graphController.getChart();

      function addScatterPlot () {
        var array = [];

        if ($attrs.series){ array.push($attrs.series); }
        array.push($attrs.field);
        if ($attrs.label || $attrs.label === '') { array.push($attrs.label); }
        scatterPlot = chart.addSeries(array, dimple.plot.bubble);
        scatterPlot.aggregate = dimple.aggregateMethod.avg;
        graphController.filter($attrs);
        graphController.draw();
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addScatterPlot();
        }
      });
    }
  };
}]);
angular.module('angular-dimple.stacked-area', [])

.directive('stackedArea', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['stackedArea', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var areaController = $controllers[0];
      var chart = graphController.getChart();

      function addArea () {
        if ($attrs.series) {
          area = chart.addSeries([$attrs.series], dimple.plot.area);
        } else {
          area = chart.addSeries([$attrs.field], dimple.plot.area);
        }
        graphController.filter($attrs);
        area.lineMarkers = false;
        graphController.draw();
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addArea();
        }
      });
    }
  };
}]);
angular.module('angular-dimple.stacked-bar', [])

.directive('stackedBar', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['stackedBar', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var lineController = $controllers[0];
      var chart = graphController.getChart();

      function addBar () {
        if ($attrs.series) {
          bar = chart.addSeries([$attrs.series], dimple.plot.bar);
        } else {
          bar = chart.addSeries([$attrs.field], dimple.plot.bar);
        }
        graphController.filter($attrs);
        graphController.draw();
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addBar();
        }
      });
    }
  };
}]);
angular.module('angular-dimple.x', [])

.directive('x', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['x', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var chart = graphController.getChart();

      function addAxis () {
        if ($attrs.groupBy) {
          if ($attrs.type == 'Measure') {
            x = chart.addMeasureAxis('x', [$attrs.groupBy, $attrs.field]);
          } else if ($attrs.type == 'Percent') {
            x = chart.addPctAxis('x', $attrs.field);
          } else if ($attrs.type == 'Time') {
            x = chart.addTimeAxis('x', $attrs.field);
            if ($attrs.format) {
              x.tickFormat = $attrs.format;
            }
          } else {
            x = chart.addCategoryAxis('x', [$attrs.groupBy, $attrs.field]);
          }
          if ($attrs.orderBy) {
            x.addGroupOrderRule($attrs.orderBy);
          }
        } else {
          if ($attrs.type == 'Measure') {
            x = chart.addMeasureAxis('x', $attrs.field);
          } else if ($attrs.type == 'Percent') {
            x = chart.addPctAxis('x', $attrs.field);
          } else if ($attrs.type == 'Time') {
            x = chart.addTimeAxis('x', $attrs.field);
            if ($attrs.format) {
              x.tickFormat = $attrs.format;
            }
          } else {
            x = chart.addCategoryAxis('x', $attrs.field);
          }
          if ($attrs.orderBy) {
            x.addOrderRule($attrs.orderBy);
          }
        }

        if ($attrs.title && $attrs.title !== "null") {
          x.title = $attrs.title;
        } else if ($attrs.title == "null") {
          x.title = null;
        }
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addAxis();
        }
      });
    }
  };
}]);
angular.module('angular-dimple.y', [])

.directive('y', [function () {
  return {
    restrict: 'E',
    replace: true,
    require: ['y', '^graph'],
    controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
    }],
    link: function($scope, $element, $attrs, $controllers) {
      var graphController = $controllers[1];
      var chart = graphController.getChart();

      function addAxis () {
        if ($attrs.groupBy) {
          if ($attrs.type == 'Category') {
            y = chart.addCategoryAxis('y', $attrs.field);
          } else if ($attrs.type == 'Percent') {
            y = chart.addPctAxis('y', $attrs.field);
          } else if ($attrs.type == 'Time') {
            y = chart.addTimeAxis('x', $attrs.field);
            if ($attrs.format) {
              y.tickFormat = $attrs.format;
            }
          } else {
            y = chart.addMeasureAxis('y', $attrs.field);
          }
          if ($attrs.orderBy) {
            y.addGroupOrderRule($attrs.orderBy);
          }
        } else {
          if ($attrs.type == 'Category') {
            y = chart.addCategoryAxis('y', $attrs.field);
          } else if ($attrs.type == 'Percent') {
            y = chart.addPctAxis('y', $attrs.field);
          } else if ($attrs.type == 'Time') {
            y = chart.addTimeAxis('x', $attrs.field);
            if ($attrs.format) {
              y.tickFormat = $attrs.format;
            }
          } else {
            y = chart.addMeasureAxis('y', $attrs.field);
          }
          if ($attrs.orderBy) {
            y.addOrderRule($attrs.orderBy);
          }
        }

        /* DMcQ: Y title is now set in graph directive
        if ($attrs.title && $attrs.title !== "null") {
          y.title = $attrs.title;
        } else if ($attrs.title == "null") {
          y.title = null;
        }
        */
        y.title = " ";
      }

      $scope.$watch('dataReady', function(newValue, oldValue) {
        if (newValue === true) {
          addAxis();
        }
      });
    }
  };
}]);