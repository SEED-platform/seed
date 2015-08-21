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

