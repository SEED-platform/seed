/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// create dummy angularJS app to attach filter(s)
var myignoremapApp = angular.module('myignoremapApp', ['ignoremap']);

describe('The ignoremap filter', function() {
    beforeEach(module('myignoremapApp'));
    it('replaces `""` with `------ Ignore Row ------`',
        inject(function(ignoremapFilter) {
            // normal cases
            expect(ignoremapFilter('')).toBe('------ Ignore Row ------');
            expect(ignoremapFilter(' ')).toBe(' ');
            expect(ignoremapFilter('aignoremap')).toBe('aignoremap');
            expect(ignoremapFilter('ignoremap ')).toBe('ignoremap ');
            expect(ignoremapFilter('ok')).toBe('ok');
            expect(ignoremapFilter(undefined)).toBe('------ Ignore Row ------');
            expect(ignoremapFilter(null)).toBe('------ Ignore Row ------');
        })
    );
});

