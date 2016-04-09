/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// create dummy angularJS app to attach filter(s)
var myTitleCaseApp = angular.module('myTitleCaseApp', ['titleCase']);

describe('The TitleCase filter', function() {
    beforeEach(module('myTitleCaseApp'));
    it('Strips out ``_`` characters from strings and capitalizes the rest',
        inject(function(titleCaseFilter) {
            // normal cases
            expect(titleCaseFilter('super_data')).toBe('Super Data');
            expect(titleCaseFilter('super_data_45')).toBe('Super Data 45');
            expect(titleCaseFilter(undefined)).toBe(undefined);
            expect(titleCaseFilter(null)).toBe(null);
        })
    );
});

