/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// taken from the angularjs testing page
// http://docs.angularjs.org/guide/dev_guide.unit-testing

// create dummy angularJS app to attach filter(s)
var myBELabelDirectiveApp = angular.module('myBELabelDirectiveApp', ['beLabel']);

describe("The beLabel directive", function() {
    var $compile;
    var $rootScope;
    beforeEach(module('myBELabelDirectiveApp'));
    // Store references to $rootScope and $compile
    // so they are available to all tests in this describe block
    beforeEach(inject(function(_$compile_, _$rootScope_){
      // The injector unwraps the underscores (_) from around the parameter names when matching
      $compile = _$compile_;
      $rootScope = _$rootScope_;
    }));

    it('Replaces the element with the appropriate content', function() {
        // Compile a piece of HTML containing the directive
        var element = $compile('<be-label name="compliant" color="blue"></be-label>')($rootScope);
        // fire all the watches
        $rootScope.$digest();
        // Check that the compiled element contains the templated content
        expect(element.hasClass('label-primary')).toBe(true);
        expect(element.hasClass('label')).toBe(true);
        expect(element.html()).toContain("compliant");
    });

        // 'red': 'danger',
        // 'gray': 'default',
        // 'orange': 'warning',
        // 'green': 'success',
        // 'blue': 'primary',
        // 'light blue': 'info'
    it('Maps colors to semantic bootstrap class names', function() {
        var element = $compile('<be-label name="compliant" color="red"></be-label>')($rootScope);
        $rootScope.$digest();
        expect(element.hasClass('label-danger')).toBe(true);

        element = $compile('<be-label name="compliant" color="gray"></be-label>')($rootScope);
        $rootScope.$digest();
        expect(element.hasClass('label-default')).toBe(true);

        element = $compile('<be-label name="compliant" color="orange"></be-label>')($rootScope);
        $rootScope.$digest();
        expect(element.hasClass('label-warning')).toBe(true);

        element = $compile('<be-label name="compliant" color="green"></be-label>')($rootScope);
        $rootScope.$digest();
        expect(element.hasClass('label-success')).toBe(true);

        element = $compile('<be-label name="compliant" color="blue"></be-label>')($rootScope);
        $rootScope.$digest();
        expect(element.hasClass('label-primary')).toBe(true);

        element = $compile('<be-label name="compliant" color="light blue"></be-label>')($rootScope);
        $rootScope.$digest();
        expect(element.hasClass('label-info')).toBe(true);
    });


});
