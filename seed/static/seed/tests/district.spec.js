/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// create dummy angularJS app to attach filter(s)
var myDistrictApp = angular.module('myDistrictApp', ['district']);

describe('The district filter', function () {
  beforeEach(module('myDistrictApp'));
  it('replaces `district` with `County/District/Ward/Borough`',
    inject(function (districtFilter) {
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
    })
  );
});

