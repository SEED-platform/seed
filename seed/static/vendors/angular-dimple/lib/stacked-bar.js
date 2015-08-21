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