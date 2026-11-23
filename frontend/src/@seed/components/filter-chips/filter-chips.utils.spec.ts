import type { ColDef, GridApi } from 'ag-grid-community'
import type { Column } from '@seed/api'
import type { AgFilterModel } from 'app/modules/inventory/inventory.types'
import { buildFilterChips, buildFilterDisplayName, removeGridFilter } from './filter-chips.utils'

describe('filter-chips utils', () => {
  const columnDefs: ColDef[] = [
    { field: 'address_line_1', headerName: 'Address Line 1' },
    { field: 'gross_floor_area', headerName: 'Gross Floor Area' },
    { field: 'cycle_start', headerName: 'Cycle Start' },
  ]

  describe('buildFilterDisplayName', () => {
    it('describes a simple text filter', () => {
      expect(buildFilterDisplayName(columnDefs[0], { filterType: 'text', type: 'contains', filter: 'Main' })).toBe('Address Line 1 contains Main')
    })

    it('joins multiple conditions with the operator', () => {
      const model = {
        filterType: 'number',
        operator: 'AND' as const,
        conditions: [
          { type: 'greaterThan' as const, filter: 100 },
          { type: 'lessThan' as const, filter: 500 },
        ],
      }
      expect(buildFilterDisplayName(columnDefs[1], model)).toBe('Gross Floor Area > 100 and < 500')
    })

    it('uses the date portion of date filters', () => {
      expect(buildFilterDisplayName(columnDefs[2], { filterType: 'date', type: 'equals', dateFrom: '2020-01-01 00:00:00', dateTo: null })).toBe(
        'Cycle Start = 2020-01-01',
      )
    })

    it('uses the date portion of floating date filters, which separate the time with T', () => {
      expect(buildFilterDisplayName(columnDefs[2], { filterType: 'date', type: 'greaterThan', dateFrom: '2020-01-01T00:00:00' })).toBe(
        'Cycle Start > 2020-01-01',
      )
    })

    it('describes number and date ranges', () => {
      expect(buildFilterDisplayName(columnDefs[1], { filterType: 'number', type: 'inRange', filter: 100, filterTo: 500 })).toBe(
        'Gross Floor Area is between 100 and 500',
      )
      const dateRange = { filterType: 'date', type: 'inRange' as const, dateFrom: '2020-01-01 00:00:00', dateTo: '2020-12-31T00:00:00' }
      expect(buildFilterDisplayName(columnDefs[2], dateRange)).toBe('Cycle Start is between 2020-01-01 and 2020-12-31')
    })
  })

  describe('buildFilterChips', () => {
    it('builds one chip per filtered column, falling back to the column display name or the filter key', () => {
      const filterModel: AgFilterModel = {
        address_line_1: { filterType: 'text', type: 'blank' },
        missing_col: { filterType: 'text', type: 'contains', filter: 'x' },
        // An access level, which has a grid column but no column def
        Building: { filterType: 'text', type: 'contains', filter: 'north' },
      }
      const columns = [{ name: 'missing_col', display_name: 'Missing Column' }] as Column[]

      expect(buildFilterChips({ filterModel, columnDefs, columns })).toEqual([
        { field: 'address_line_1', displayName: 'Address Line 1 is blank', original: 'address_line_1' },
        { field: 'missing_col', displayName: 'Missing Column contains x', original: 'missing_col' },
        { field: 'Building', displayName: 'Building contains north', original: 'Building' },
      ])
    })

    it("describes the legacy UI's filters by their keys' columns and lookups", () => {
      const filterModel = { address_line_1__icontains: 'Main', gross_floor_area__gte: '100', missing_col: 'x', cycle_start__isnull: 'true' }
      const columns = [{ name: 'missing_col', display_name: 'Missing Column' }] as Column[]

      expect(buildFilterChips({ filterModel, columnDefs, columns })).toEqual([
        { field: 'address_line_1', displayName: 'Address Line 1 contains Main', original: 'address_line_1__icontains' },
        { field: 'gross_floor_area', displayName: 'Gross Floor Area >= 100', original: 'gross_floor_area__gte' },
        { field: 'missing_col', displayName: 'Missing Column = x', original: 'missing_col' },
        // A lookup the legacy UI doesn't use, as is
        { field: 'cycle_start__isnull', displayName: 'cycle_start__isnull = true', original: 'cycle_start__isnull' },
      ])
    })

    it('returns no chips for an empty filter model', () => {
      expect(buildFilterChips({ filterModel: {}, columnDefs })).toEqual([])
    })
  })

  describe('removeGridFilter', () => {
    it('clears only the requested column filter', () => {
      const gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['getFilterModel', 'setFilterModel'])
      gridApi.getFilterModel.and.returnValue({ a: { type: 'blank' }, b: { type: 'notBlank' } })

      removeGridFilter(gridApi, 'a')

      expect(gridApi.setFilterModel).toHaveBeenCalledWith({ b: { type: 'notBlank' } })
    })
  })
})
