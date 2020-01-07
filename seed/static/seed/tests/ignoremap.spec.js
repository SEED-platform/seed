/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// create dummy angularJS app to attach filter(s)
var myignoremapApp = angular.module('myignoremapApp', ['ignoremap']);

describe('The ignoremap filter', function () {
  var ignoremapFilter;

  beforeEach(function () {
    module('myignoremapApp');
    inject(function (_ignoremapFilter_) {
      ignoremapFilter = _ignoremapFilter_;
    });
  });

  it('replaces `""` with `------ Ignore Row ------`', function () {
    // normal cases
    expect(ignoremapFilter('')).toBe('------ Ignore Row ------');
    expect(ignoremapFilter(' ')).toBe(' ');
    expect(ignoremapFilter('aignoremap')).toBe('aignoremap');
    expect(ignoremapFilter('ignoremap ')).toBe('ignoremap ');
    expect(ignoremapFilter('ok')).toBe('ok');
    expect(ignoremapFilter(undefined)).toBe('------ Ignore Row ------');
    expect(ignoremapFilter(null)).toBe('------ Ignore Row ------');
  });
});

