/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('The sdLabel directive', () => {
  let $compile;
  let $rootScope;
  beforeEach(() => {
    module('SEED');
    inject((_$compile_, _$httpBackend_, _$rootScope_) => {
      $compile = _$compile_;
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
      $rootScope = _$rootScope_;
    });
  });

  it('Replaces the element with the appropriate content', () => {
    // Compile a piece of HTML containing the directive
    const element = $compile('<sd-label name="compliant" color="blue"></sd-label>')($rootScope);
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
  it('Maps colors to semantic bootstrap class names', () => {
    let element = $compile('<sd-label name="compliant" color="red"></sd-label>')($rootScope);
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
