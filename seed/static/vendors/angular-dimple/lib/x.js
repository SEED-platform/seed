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