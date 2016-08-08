/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

/**
 * UI Grid overrides
 */
angular.module('ui.grid').config(['$provide', function ($provide) {
  $provide.decorator('i18nService', ['$delegate', function ($delegate) {
    var pagination = $delegate.get('en').pagination;
    pagination.sizes = 'properties per page';
    pagination.totalItems = 'properties';
    $delegate.add('en', {pagination: pagination});
    return $delegate;
  }]);
  $provide.decorator('uiGridGridMenuService', ['$delegate', 'i18nService', 'gridUtil', function ($delegate, i18nService, gridUtil) {
    $delegate.getMenuItems = function ($scope) {
      var menuItems = [];
      if ($scope.grid.options.gridMenuCustomItems) {
        if (!angular.isArray($scope.grid.options.gridMenuCustomItems)) {
          gridUtil.logError('gridOptions.gridMenuCustomItems must be an array, and is not');
        } else {
          menuItems = menuItems.concat($scope.grid.options.gridMenuCustomItems);
        }
      }
      var clearFilters = [{
        title: i18nService.getSafeText('gridMenu.clearAllFilters'),
        action: function ($event) {
          $scope.grid.clearAllFilters();
        },
        shown: function () {
          return $scope.grid.options.enableFiltering;
        },
        order: 100
      }];
      menuItems = menuItems.concat(clearFilters);
      menuItems = menuItems.concat($scope.registeredMenuItems);
      if ($scope.grid.options.gridMenuShowHideColumns !== false) {
        menuItems = menuItems.concat($delegate.showHideColumns($scope));
      }
      menuItems.sort(function (a, b) {
        return a.order - b.order;
      });
      return menuItems;
    };
    return $delegate;
  }]);
  $provide.decorator('uiGridMenuItemDirective', ['$delegate', 'gridUtil', '$compile', 'i18nService', function ($delegate, gridUtil, $compile, i18nService) {
    $delegate[0].compile = function () {
      return {
        pre: function ($scope, $elm) {
          if ($scope.templateUrl) {
            gridUtil.getTemplate($scope.templateUrl)
              .then(function (contents) {
                var template = angular.element(contents);

                var newElm = $compile(template)($scope);
                $elm.replaceWith(newElm);
              });
          }
        },
        post: function ($scope, $elm, $attrs, controllers) {
          var uiGridCtrl = controllers[0];

          // TODO(c0bra): validate that shown and active are functions if they're defined. An exception is already thrown above this though
          // if (typeof($scope.shown) !== 'undefined' && $scope.shown && typeof($scope.shown) !== 'function') {
          //   throw new TypeError("$scope.shown is defined but not a function");
          // }
          if (typeof($scope.shown) === 'undefined' || $scope.shown === null) {
            $scope.shown = function () {
              return true;
            };
          }

          $scope.itemShown = function () {
            var context = {};
            if ($scope.context) {
              context.context = $scope.context;
            }

            if (typeof(uiGridCtrl) !== 'undefined' && uiGridCtrl) {
              context.grid = uiGridCtrl.grid;
            }

            return $scope.shown.call(context);
          };

          $scope.itemAction = function ($event, title) {
            $event.stopPropagation();

            if (typeof($scope.action) === 'function') {
              var context = {};

              if ($scope.context) {
                context.context = $scope.context;
              }

              // Add the grid to the function call context if the uiGrid controller is present
              if (typeof(uiGridCtrl) !== 'undefined' && uiGridCtrl) {
                context.grid = uiGridCtrl.grid;
              }

              $scope.action.call(context, $event, title);

              if (!$scope.leaveOpen) {
                $scope.$emit('hide-menu');
              } else {
                /*
                 * XXX: Fix after column refactor
                 * Ideally the focus would remain on the item.
                 * However, since there are two menu items that have their 'show' property toggled instead. This is a quick fix.
                 */

                var id = parseInt($elm[0].id.match(/\d+/)[0]);
                var selector = '#menuitem-' + (id % 2 ? id + 1 : id - 1);
                gridUtil.focus.bySelector(angular.element(selector), 'button[type=button]', true);
              }
            }
          };

          $scope.i18n = i18nService.get();
        }
      };
    };
    return $delegate;
  }]);
}]);
