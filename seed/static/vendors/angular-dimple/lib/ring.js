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

