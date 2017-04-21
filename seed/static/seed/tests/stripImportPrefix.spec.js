/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// create dummy angularJS app to attach filter(s)
var myStripFilterApp = angular.module('myStripFilterApp', ['stripImportPrefix']);

describe('The stripImportPrefix filter', function() {
    beforeEach(module('myStripFilterApp'));
    it('Strips out the import prefix from building ids',
        // e.g. remove the 'IMP12-' from the id 'IMP12-1321/123'
        inject(function(stripImportPrefixFilter) {
            // normal cases
            expect(stripImportPrefixFilter('IMP134-134')).toBe('134');
            expect(stripImportPrefixFilter('IMP134555-134')).toBe('134');
            expect(stripImportPrefixFilter('IMP1-134')).toBe('134');
            expect(stripImportPrefixFilter('IMP0-134')).toBe('134');
            // deals with `-`
            expect(stripImportPrefixFilter('IMP134-abc-dev')).toBe('abc-dev');
            // deals with `/`
            expect(stripImportPrefixFilter('IMP134-00/11')).toBe('00/11');
            // only strips first prefix
            expect(stripImportPrefixFilter('IMP134-IMP134-123')).toBe('IMP134-123');
        })
    );
    it('Does not strip out anything if there is not a prefix',
        inject(function(stripImportPrefixFilter) {
            // normal cases
            expect(stripImportPrefixFilter('123-123')).toBe('123-123');
            expect(stripImportPrefixFilter('0123/123')).toBe('0123/123');
        })
    );
    it('Is case sensitive to the import prefix',
        inject(function(stripImportPrefixFilter) {
            expect(stripImportPrefixFilter('imp123-abc')).toBe('imp123-abc');
            expect(stripImportPrefixFilter('iMp123-abc')).toBe('iMp123-abc');
            expect(stripImportPrefixFilter('iMP123-abc')).toBe('iMP123-abc');
        })
    );
    it('Handles undefined or null inputs',
        inject(function(stripImportPrefixFilter) {
            expect(stripImportPrefixFilter(undefined)).toBe(undefined);
            expect(stripImportPrefixFilter(null)).toBe(null);
        })
    );
    it('Only strips out the prefix if it has at least one digit and a hyphen',
        inject(function(stripImportPrefixFilter) {
            // must have the 'IMP' folowed by a digit then a hyphen
            expect(stripImportPrefixFilter('IMP-123')).toBe('IMP-123');
            expect(stripImportPrefixFilter('IMP1123')).toBe('IMP1123');
        })
    );
});
