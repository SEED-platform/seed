/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('The ignoremap filter', () => {
  let ignoremapFilter;

  beforeEach(() => {
    module('BE.seed');
    inject((_ignoremapFilter_) => {
      ignoremapFilter = _ignoremapFilter_;
    });
  });

  it('replaces `""` with `------ Ignore Row ------`', () => {
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
