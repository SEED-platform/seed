/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('sdDropdown', [])
  .directive('sdDropdown', ['urls', function (urls) {
    return {
      restrict: 'E',
      require: '^ngModel',
      scope: {
        ngModel: '=', // selection
        items: '=', // items to select from
        callback: '&' // callback
      },
      link: function (scope, element, attrs) {
        element.on('click', function (event) {
          event.preventDefault();
        });

        scope.default = 'Please select item';
        scope.isButton = 'isButton' in attrs;

        // selection changed handler
        scope.select = function (item) {
          scope.ngModel = item;
          if (scope.callback) {
            scope.callback({ item: item });
          }
        };
      },
      templateUrl: urls.static_url + 'seed/js/directives/sd-dropdown-template.html'
    };
  }]);
