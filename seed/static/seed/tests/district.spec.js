/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
// create dummy angularJS app to attach filter(s)
const myDistrictApp = angular.module('myDistrictApp', ['district']);

describe('The district filter', () => {
  let districtFilter;

  beforeEach(() => {
    module('myDistrictApp');
    inject((_districtFilter_) => {
      districtFilter = _districtFilter_;
    });
  });
  it('replaces `district` with `County/District/Ward/Borough`', () => {
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
