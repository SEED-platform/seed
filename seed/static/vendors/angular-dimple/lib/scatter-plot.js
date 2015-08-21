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