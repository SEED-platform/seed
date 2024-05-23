/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('The TitleCase filter', () => {
  let titleCaseFilter;

  beforeEach(() => {
    module('BE.seed');
    inject((_titleCaseFilter_) => {
      titleCaseFilter = _titleCaseFilter_;
    });
  });

  it('Strips out ``_`` characters from strings and capitalizes the rest', () => {
    // normal cases
    expect(titleCaseFilter('super_data')).toBe('Super Data');
    expect(titleCaseFilter('super_data_45')).toBe('Super Data 45');
    expect(titleCaseFilter(undefined)).toBe(undefined);
    expect(titleCaseFilter(null)).toBe(null);
  });
});
