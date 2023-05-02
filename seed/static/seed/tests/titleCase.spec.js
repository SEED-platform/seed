/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// create dummy angularJS app to attach filter(s)
var myTitleCaseApp = angular.module('myTitleCaseApp', ['titleCase']);

describe('The TitleCase filter', function () {
  var titleCaseFilter;

  beforeEach(function () {
    module('myTitleCaseApp');
    inject(function (_titleCaseFilter_) {
      titleCaseFilter = _titleCaseFilter_;
    });
  });

  it('Strips out ``_`` characters from strings and capitalizes the rest', function () {
    // normal cases
    expect(titleCaseFilter('super_data')).toBe('Super Data');
    expect(titleCaseFilter('super_data_45')).toBe('Super Data 45');
    expect(titleCaseFilter(undefined)).toBe(undefined);
    expect(titleCaseFilter(null)).toBe(null);
  });
});
