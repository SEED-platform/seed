/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// taken from the angularjs testing page
// http://docs.angularjs.org/guide/dev_guide.unit-testing

// create dummy angularJS app to attach filter(s)
var mySDLabelDirectiveApp = angular.module('mySDLabelDirectiveApp', ['sdLabel'],
  ['$interpolateProvider', '$qProvider', function ($interpolateProvider, $qProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
    $qProvider.errorOnUnhandledRejections(false);
  }]);

describe('The sdLabel directive', function () {
  var $compile;
  var $rootScope;
  beforeEach(function () {
    module('mySDLabelDirectiveApp');
    inject(function (_$compile_, _$rootScope_) {
      // The injector unwraps the underscores (_) from around the parameter names when matching
      $compile = _$compile_;
      $rootScope = _$rootScope_;
    });
  });

  it('Replaces the element with the appropriate content', function () {
    // Compile a piece of HTML containing the directive
    var element = $compile('<sd-label name="compliant" color="blue"></sd-label>')($rootScope);
    // fire all the watches
    $rootScope.$digest();
    // Check that the compiled element contains the templated content
    expect(element.hasClass('label-primary')).toBe(true);
    expect(element.hasClass('label')).toBe(true);
    expect(element.html()).toContain('compliant');
  });

  // 'red': 'danger',
  // 'gray': 'default',
  // 'orange': 'warning',
  // 'green': 'success',
  // 'blue': 'primary',
  // 'light blue': 'info'
  it('Maps colors to semantic bootstrap class names', function () {
    var element = $compile('<sd-label name="compliant" color="red"></sd-label>')($rootScope);
    $rootScope.$digest();
    expect(element.hasClass('label-danger')).toBe(true);

    element = $compile('<sd-label name="compliant" color="gray"></sd-label>')($rootScope);
    $rootScope.$digest();
    expect(element.hasClass('label-default')).toBe(true);

    element = $compile('<sd-label name="compliant" color="orange"></sd-label>')($rootScope);
    $rootScope.$digest();
    expect(element.hasClass('label-warning')).toBe(true);

    element = $compile('<sd-label name="compliant" color="green"></sd-label>')($rootScope);
    $rootScope.$digest();
    expect(element.hasClass('label-success')).toBe(true);

    element = $compile('<sd-label name="compliant" color="blue"></sd-label>')($rootScope);
    $rootScope.$digest();
    expect(element.hasClass('label-primary')).toBe(true);

    element = $compile('<sd-label name="compliant" color="light blue"></sd-label>')($rootScope);
    $rootScope.$digest();
    expect(element.hasClass('label-info')).toBe(true);
  });


});
