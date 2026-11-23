import type { GridApi } from 'ag-grid-community'
import type { FiltersSorts } from '../../../inventory/inventory.types'
import { FilterSortChipsComponent } from './filter-sort-chips.component'

describe('FilterSortChipsComponent removing chips', () => {
  const filters = {
    address_line_1_1: { filterType: 'text', type: 'contains', filter: 'Main' },
    removed_column_2: { filterType: 'number', type: 'equals', filter: 1 },
  }
  let component: FilterSortChipsComponent
  let gridApi: jasmine.SpyObj<GridApi>
  let removed: FiltersSorts[]

  beforeEach(() => {
    gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['getFilterModel', 'setFilterModel', 'getColumnState', 'applyColumnState'])
    gridApi.getFilterModel.and.returnValue({ address_line_1_1: { ...filters.address_line_1_1 } })
    gridApi.getColumnState.and.returnValue([{ colId: 'site_eui_3', sort: 'desc' }])
    component = new FilterSortChipsComponent()
    component.gridApi = gridApi
    component.type = 'properties'
    component.userSettings = { filters: { properties: filters }, sorts: { properties: ['-site_eui_3', 'removed_column_2'] } }
    removed = []
    component.savedFilterSortRemoved.subscribe((filtersSorts) => removed.push(filtersSorts))
  })

  it("removes the grid's filters and sorts from the grid", () => {
    component.removeFilter('address_line_1_1')
    component.removeSort('site_eui_3')

    expect(gridApi.setFilterModel).toHaveBeenCalledWith({})
    expect(gridApi.applyColumnState).toHaveBeenCalledWith({ state: [{ colId: 'site_eui_3', sort: null }] })
    expect(removed).toEqual([])
  })

  // e.g., on columns outside the profile, which only the server applies
  it("removes saved filters and sorts the grid doesn't have from the saved ones", () => {
    component.removeFilter('removed_column_2')
    component.removeSort('removed_column_2')

    expect(removed).toEqual([
      { filters: { address_line_1_1: filters.address_line_1_1 }, sorts: ['-site_eui_3', 'removed_column_2'] },
      { filters, sorts: ['-site_eui_3'] },
    ])
    expect(gridApi.setFilterModel).not.toHaveBeenCalled()
    expect(gridApi.applyColumnState).not.toHaveBeenCalled()
  })
})
