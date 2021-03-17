/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// create dummy angularJS app to attach filter(s)
var myDistrictApp = angular.module('myDistrictApp', ['district']);

describe('The district filter', function () {
  var districtFilter;

  beforeEach(function () {
    module('myDistrictApp');
    inject(function (_districtFilter_) {
      districtFilter = _districtFilter_;
    });
  });
  it('replaces `district` with `County/District/Ward/Borough`', function () {
    // normal cases
    expect(districtFilter('district')).toBe('County/District/Ward/Borough');
    expect(districtFilter('District')).toBe('County/District/Ward/Borough');
    expect(districtFilter('DistRict')).toBe('County/District/Ward/Borough');
    expect(districtFilter('DISTRICT')).toBe('County/District/Ward/Borough');
    expect(districtFilter('aDISTRICT')).toBe('aDISTRICT');
    expect(districtFilter('')).toBe('');
    expect(districtFilter('district ')).toBe('district ');
    expect(districtFilter('ok')).toBe('ok');
    expect(districtFilter(undefined)).toBe(undefined);
    expect(districtFilter(null)).toBe(null);
  });
});
