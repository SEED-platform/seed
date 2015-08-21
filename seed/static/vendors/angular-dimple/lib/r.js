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