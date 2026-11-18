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
  })

  describe('buildFilterChips', () => {
    it('builds one chip per filtered column, falling back to the column display name', () => {
      const filterModel: AgFilterModel = {
        address_line_1: { filterType: 'text', type: 'blank' },
        missing_col: { filterType: 'text', type: 'contains', filter: 'x' },
      }
      const columns = [{ name: 'missing_col', display_name: 'Missing Column' }] as Column[]

      expect(buildFilterChips({ filterModel, columnDefs, columns })).toEqual([
        { field: 'address_line_1', displayName: 'Address Line 1 is blank', original: 'address_line_1' },
        { field: 'missing_col', displayName: 'Missing Column', original: 'missing_col' },
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
