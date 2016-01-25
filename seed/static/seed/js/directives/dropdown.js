/*
 * :copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('dropdown', [])
.directive('seedDropdown', ['urls', function (urls) {
  return {
    restrict: 'E',
    require: '^ngModel',
    scope: {
      ngModel: '=', // selection
      items: '=',   // items to select from
      callback: '&' // callback
    },
    link: function(scope, element, attrs) {
      element.on('click', function(event) {
        event.preventDefault();
      });

      scope.default = 'Please select item';
      scope.isButton = 'isButton' in attrs;

      // selection changed handler
      scope.select = function(item) {
        scope.ngModel = item;
        if (scope.callback) {
          scope.callback({ item: item });
        }
      };
    },
    templateUrl: urls.static_url + 'seed/js/directives/dropdown-template.html'
  };
}]);
