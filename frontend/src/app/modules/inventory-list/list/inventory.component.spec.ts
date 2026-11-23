import type { ColDef, GridApi } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { Subject } from 'rxjs'
import type { Profile } from 'app/modules/inventory'
import { applyColumnProfile, InventoryComponent, savedFilterModel, updatePageSelection, withLoadingOverlay } from './inventory.component'

describe('InventoryComponent profile columns', () => {
  it('applies saved order and pins using unique API field IDs', () => {
    const profile: Profile = {
      id: 1,
      name: 'Test profile',
      inventory_type: 'Property',
      profile_location: 'List View Profile',
      columns: [
        {
          id: 11,
          column_name: 'address_line_1',
          display_name: 'Address',
          name: 'address_line_1',
          table_name: 'PropertyState',
          order: 2,
          pinned: false,
        },
        {
          id: 22,
          column_name: 'address_line_1',
          display_name: 'Address',
          name: 'address_line_1',
          table_name: 'TaxLotState',
          order: 1,
          pinned: true,
        },
      ],
    }
    const columnDefs: ColDef[] = [{ field: 'address_line_1_11' }, { field: 'address_line_1_22' }, { field: 'other' }]

    const result = applyColumnProfile(profile, columnDefs)

    expect(result.map((column) => [column.field, column.pinned])).toEqual([
      ['address_line_1_22', 'left'],
      ['address_line_1_11', null],
      ['other', undefined],
    ])
    expect(columnDefs[0].field).toBe('address_line_1_11')
  })

  it('keeps the API definitions unchanged when no profile is selected', () => {
    const columnDefs: ColDef[] = [{ field: 'address_line_1' }]
    expect(applyColumnProfile(null, columnDefs)).toBe(columnDefs)
  })
})

describe('InventoryComponent page selection', () => {
  it('preserves selected IDs from other pages while updating the current page', () => {
    expect(updatePageSelection([1, 2, 3, 4], [1, 2], [2])).toEqual([3, 4, 2])
  })

  it('removes only the current page IDs when all its rows are unchecked', () => {
    expect(updatePageSelection([1, 2, 3, 4], [1, 2], [])).toEqual([3, 4])
  })
})

describe('InventoryComponent saved filters', () => {
  const columnDefs: ColDef[] = [{ field: 'address_line_1_1' }, { field: 'long_lat_2', filter: false }]
  const filters = {
    address_line_1_1: { filterType: 'text', type: 'contains', filter: 'Main' },
    long_lat_2: { filterType: 'text', type: 'notBlank' },
    Root: { filterType: 'text', type: 'equals', filter: 'All' },
    Building: { filterType: 'text', type: 'equals', filter: 'A' },
    removed_column_3: { filterType: 'number', type: 'equals', filter: 1 },
  }

  it('keeps filters on filterable API columns and non-root access level columns', () => {
    expect(savedFilterModel({ filters, columnDefs, accessLevelNames: ['Root', 'Building'] })).toEqual({
      address_line_1_1: filters.address_line_1_1,
      Building: filters.Building,
    })
  })

  it('copies the saved filters, which AG Grid would otherwise share', () => {
    const model = savedFilterModel({ filters, columnDefs, accessLevelNames: [] }) as typeof filters
    model.address_line_1_1.filter = 'Oak'
    expect(filters.address_line_1_1.filter).toBe('Main')
  })
})

describe('InventoryComponent saved sorts', () => {
  it('sorts the next column defs without reporting a sort change', () => {
    const columnDefs: ColDef[] = [{ field: 'address_line_1_1' }, { field: 'site_eui_2' }, { field: 'gross_floor_area_3' }]
    const gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['applyColumnState', 'onSortChanged'])
    const component = Object.assign(Object.create(InventoryComponent.prototype) as InventoryComponent, {
      type: 'properties',
      columnDefs,
      gridApi,
      userSettings: { sorts: { properties: ['-site_eui_2', 'gross_floor_area_3', 'removed_column_4'] } },
    })

    component.setSorts()

    expect(columnDefs.map(({ sort }) => sort)).toEqual([undefined, 'desc', 'asc'])
    expect(gridApi.applyColumnState).not.toHaveBeenCalled()
    expect(gridApi.onSortChanged).not.toHaveBeenCalled()
  })
})

describe('InventoryComponent filter and sort changes', () => {
  const filters = {
    address_line_1_1: { filterType: 'text', type: 'contains', filter: 'Main' },
    Building: { filterType: 'text', type: 'equals', filter: 'A' },
  }
  let component: InventoryComponent
  let refresh: jasmine.Spy

  beforeEach(() => {
    // Without Angular, which onFilterSortChange doesn't use
    component = Object.assign(Object.create(InventoryComponent.prototype) as InventoryComponent, {
      type: 'properties',
      page: 3,
      refreshInventory$: new Subject<number | null>(),
      userSettings: { filters: { properties: structuredClone(filters) }, sorts: { properties: ['-site_eui_2'] } },
      requestedFilterSorts: { filters: structuredClone(filters), sorts: ['-site_eui_2'] },
    })
    refresh = spyOn(component.refreshInventory$, 'next')
  })

  it('keeps the loaded inventory for the filters and sorts it has, in any order', () => {
    const reordered = structuredClone({ Building: filters.Building, address_line_1_1: filters.address_line_1_1 })
    component.onFilterSortChange({ filters: reordered, sorts: ['-site_eui_2'] })

    expect(refresh).not.toHaveBeenCalled()
    expect(component.page).toBe(3)
  })

  it('reloads the first page for new filters or sorts', () => {
    component.onFilterSortChange({ filters: {}, sorts: ['-site_eui_2'] })
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(component.page).toBe(1)
    expect(component.userSettings.filters.properties).toEqual({})

    component.onFilterSortChange({ filters: {}, sorts: [] })
    expect(refresh).toHaveBeenCalledTimes(2)
    expect(component.userSettings.sorts.properties).toEqual([])
  })

  it('compares with the latest request, before its inventory loads', () => {
    component.onFilterSortChange({ filters: {}, sorts: ['-site_eui_2'] })
    // e.g., resetting the grid to the loaded filters before that reload
    component.onFilterSortChange({ filters: structuredClone(filters), sorts: ['-site_eui_2'] })
    component.onFilterSortChange({ filters: structuredClone(filters), sorts: ['-site_eui_2'] })
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('reloads for changes the saved filters and sorts already have', () => {
    // A sort the shared saved settings already have when the grid's (asynchronous) event reports it
    component.userSettings.sorts.properties = ['site_eui_2']
    component.onFilterSortChange({ filters, sorts: ['site_eui_2'] })
    expect(refresh).toHaveBeenCalledTimes(1)

    // Resetting the grid, which clears the saved filters and sorts first
    component.userSettings.filters.properties = {}
    component.userSettings.sorts.properties = []
    component.onFilterSortChange({ filters: {}, sorts: [] })
    expect(refresh).toHaveBeenCalledTimes(2)
  })
})

describe('withLoadingOverlay', () => {
  let setGridOption: jasmine.Spy
  let withOverlay: <T>(load$: Observable<T>) => Observable<T>

  beforeEach(() => {
    setGridOption = jasmine.createSpy('setGridOption')
    withOverlay = withLoadingOverlay(() => ({ setGridOption, isDestroyed: () => false }) as unknown as GridApi)
  })

  const loading = () => setGridOption.calls.mostRecent().args as [string, boolean]

  it('shows until every overlapping load ends', () => {
    const first = new Subject<null>()
    const second = new Subject<null>()
    withOverlay(first).subscribe()
    withOverlay(second).subscribe({ error: () => undefined })
    expect(loading()).toEqual(['loading', true])

    first.complete()
    expect(loading()).toEqual(['loading', true])
    second.error(new Error('Bad Request'))
    expect(loading()).toEqual(['loading', false])
  })

  it('hides when a newer load replaces the only pending one', () => {
    withOverlay(new Subject<null>()).subscribe().unsubscribe()
    expect(loading()).toEqual(['loading', false])
  })

  it('waits for the grid', () => {
    const grid: { api?: GridApi } = {}
    const load$ = new Subject<null>()
    withLoadingOverlay(() => grid.api)(load$).subscribe()
    grid.api = { setGridOption, isDestroyed: () => false } as unknown as GridApi
    load$.complete()
    expect(loading()).toEqual(['loading', false])
  })

  it('leaves a destroyed grid alone', () => {
    const load$ = new Subject<null>()
    withLoadingOverlay(() => ({ setGridOption, isDestroyed: () => true }) as unknown as GridApi)(load$).subscribe()
    load$.complete()
    expect(setGridOption).not.toHaveBeenCalled()
  })
})
