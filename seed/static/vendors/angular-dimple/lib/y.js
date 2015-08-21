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