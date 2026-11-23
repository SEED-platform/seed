import { Injector } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import type { ColDef, GridApi } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { of, Subject } from 'rxjs'
import type { FilterGroup, FilterGroupService, InventoryService } from '@seed/api'
import type { Profile } from 'app/modules/inventory'
import { FilterGroupSelectorComponent, FilterSortChipsComponent, InventoryGridControlsComponent } from './grid'
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
  const columnDefs: ColDef[] = [{ field: 'address_line_1_1' }, { field: 'long_lat_2', filter: false }, { field: 'city_4' }]
  const filters = {
    address_line_1_1: { filterType: 'text', type: 'contains', filter: 'Main' },
    long_lat_2: { filterType: 'text', type: 'notBlank' },
    Root: { filterType: 'text', type: 'equals', filter: 'All' },
    Building: { filterType: 'text', type: 'equals', filter: 'A' },
    removed_column_3: { filterType: 'number', type: 'equals', filter: 1 },
    // Legacy UI filters, which only the server applies
    city_4: 'Denver',
    city_4__ne: 'Boulder',
  }

  it('keeps AG Grid filters on filterable API columns and non-root access level columns', () => {
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
    // Without Angular, which these handlers don't use
    component = Object.assign(Object.create(InventoryComponent.prototype) as InventoryComponent, {
      type: 'properties',
      page: 3,
      accessLevelNames: ['Root', 'Building'],
      columnDefs: [{ field: 'address_line_1_1' }, { field: 'site_eui_2' }],
      refreshInventory$: new Subject<number | null>(),
      userSettings: { filters: { properties: structuredClone(filters) }, sorts: { properties: ['-site_eui_2'] } },
      requestedFilterSorts: { filters: structuredClone(filters), sorts: ['-site_eui_2'] },
    })
    refresh = spyOn(component.refreshInventory$, 'next')
  })

  it('keeps the loaded inventory for the filters and sorts it has, in any order', () => {
    const reordered = structuredClone({ Building: filters.Building, address_line_1_1: filters.address_line_1_1 })
    component.onGridFilterSortChange({ filters: reordered, sorts: ['-site_eui_2'] })

    expect(refresh).not.toHaveBeenCalled()
    expect(component.page).toBe(3)
  })

  it('reloads the first page for new filters or sorts', () => {
    component.onGridFilterSortChange({ filters: {}, sorts: ['-site_eui_2'] })
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(component.page).toBe(1)
    expect(component.userSettings.filters.properties).toEqual({})

    component.onGridFilterSortChange({ filters: {}, sorts: [] })
    expect(refresh).toHaveBeenCalledTimes(2)
    expect(component.userSettings.sorts.properties).toEqual([])
  })

  it('compares with the latest request, before its inventory loads', () => {
    component.onGridFilterSortChange({ filters: {}, sorts: ['-site_eui_2'] })
    // e.g., resetting the grid to the loaded filters before that reload
    component.onGridFilterSortChange({ filters: structuredClone(filters), sorts: ['-site_eui_2'] })
    component.onGridFilterSortChange({ filters: structuredClone(filters), sorts: ['-site_eui_2'] })
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('reloads for changes the saved filters and sorts already have', () => {
    // A sort the shared saved settings already have when the grid's (asynchronous) event reports it
    component.userSettings.sorts.properties = ['site_eui_2']
    component.onGridFilterSortChange({ filters, sorts: ['site_eui_2'] })
    expect(refresh).toHaveBeenCalledTimes(1)

    // Resetting the grid, which clears the saved filters and sorts first
    component.userSettings.filters.properties = {}
    component.userSettings.sorts.properties = []
    component.onGridFilterSortChange({ filters: {}, sorts: [] })
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  describe("with saved filters and sorts the grid can't show", () => {
    // On a column outside the profile, and a legacy UI filter (e.g., in its filter groups), which only the server applies
    const hiddenFilters = {
      removed_column_3: { filterType: 'number', type: 'equals', filter: 1 },
      site_eui_2__gt: '100',
    }
    const savedFilters = { ...filters, ...hiddenFilters }
    const savedSorts = ['-removed_column_3', 'site_eui_2']

    beforeEach(() => {
      Object.assign(component, {
        userSettings: { filters: { properties: structuredClone(savedFilters) }, sorts: { properties: [...savedSorts] } },
        requestedFilterSorts: structuredClone({ filters: savedFilters, sorts: savedSorts }),
      })
    })

    it('keeps them when the grid shows the saved filters and sorts it can', () => {
      component.onGridFilterSortChange({ filters, sorts: ['site_eui_2'] })

      expect(refresh).not.toHaveBeenCalled()
      expect(component.page).toBe(3)
      expect(component.userSettings).toEqual({ filters: { properties: savedFilters }, sorts: { properties: savedSorts } })
    })

    it('keeps them when a visible filter changes', () => {
      const edited = { ...filters, address_line_1_1: { ...filters.address_line_1_1, filter: 'Oak' } }
      component.onGridFilterSortChange({ filters: edited, sorts: ['site_eui_2'] })

      expect(refresh).toHaveBeenCalledTimes(1)
      expect(component.requestedFilterSorts).toEqual({ filters: { ...edited, ...hiddenFilters }, sorts: savedSorts })
      expect(component.userSettings).toEqual({ filters: { properties: { ...edited, ...hiddenFilters } }, sorts: { properties: savedSorts } })
    })

    it('keeps the hidden sorts when a visible sort is removed, while a new sort replaces them', () => {
      component.onGridFilterSortChange({ filters, sorts: [] })
      expect(component.sorts).toEqual(['-removed_column_3'])

      component.onGridFilterSortChange({ filters, sorts: ['-site_eui_2'] })
      expect(component.sorts).toEqual(['-site_eui_2'])
      expect(component.filters).toEqual(savedFilters)
      expect(refresh).toHaveBeenCalledTimes(2)
    })

    it("deletes a removed chip's", () => {
      const gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['getFilterModel', 'getColumnState'])
      gridApi.getFilterModel.and.callFake(() => structuredClone(filters))
      gridApi.getColumnState.and.returnValue([{ colId: 'site_eui_2', sort: 'asc' }])
      const chips = Object.assign(new FilterSortChipsComponent(), { gridApi, type: 'properties', userSettings: component.userSettings })
      // As the template routes them, apart from the grid's events
      chips.savedFilterSortRemoved.subscribe((filtersSorts) => {
        component.onFilterSortChange(filtersSorts)
      })

      chips.removeFilter('removed_column_3')
      chips.removeFilter('site_eui_2__gt')
      chips.removeSort('removed_column_3')

      expect(refresh).toHaveBeenCalledTimes(3)
      expect(component.requestedFilterSorts).toEqual({ filters, sorts: ['site_eui_2'] })
      expect(component.userSettings).toEqual({ filters: { properties: filters }, sorts: { properties: ['site_eui_2'] } })
    })

    it('deletes them when resetting the grid', () => {
      const gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['setFilterModel'])
      const controls = Object.assign(Object.create(InventoryGridControlsComponent.prototype) as InventoryGridControlsComponent, {
        gridApi,
        userSettings: component.userSettings,
      })
      controls.resetFilters()
      controls.resetSorts()
      // As the grid clears its filters, and then its sorts once the reset is saved
      component.onGridFilterSortChange({ filters: {}, sorts: ['site_eui_2'] })
      component.onGridFilterSortChange({ filters: {}, sorts: [] })

      expect(refresh).toHaveBeenCalledTimes(2)
      expect(component.requestedFilterSorts).toEqual({ filters: {}, sorts: [] })
      expect(component.filters).toEqual({})
      expect(component.sorts).toEqual([])
    })

    it("keeps a filter group's filters the grid can't show, e.g., the legacy UI's", () => {
      const gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['setFilterModel'])
      component.gridApi = gridApi
      const queryDict = { address_line_1_1: { filterType: 'text', type: 'equals', filter: 'Oak' }, ...hiddenFilters }
      component.onFilterGroupApplied({ query_dict: structuredClone(queryDict) })
      // The label selections' reload, before the grid's (asynchronous) event
      component.requestedFilterSorts = structuredClone({ filters: component.filters, sorts: component.sorts })
      component.onGridFilterSortChange({ filters: { address_line_1_1: queryDict.address_line_1_1 }, sorts: ['site_eui_2'] })

      expect(gridApi.setFilterModel).toHaveBeenCalledOnceWith({ address_line_1_1: queryDict.address_line_1_1 })
      expect(refresh).not.toHaveBeenCalled()
      expect(component.filters).toEqual(queryDict)
    })

    it('keeps them when deselecting a filter group', () => {
      const gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['getFilterModel'])
      gridApi.getFilterModel.and.returnValue(structuredClone(filters))
      component.gridApi = gridApi
      component.onFilterGroupApplied(null)

      expect(component.filters).toEqual(savedFilters)
    })

    it('saves them in filter groups', () => {
      const filterGroupService = jasmine.createSpyObj<FilterGroupService>('FilterGroupService', ['create', 'update'])
      filterGroupService.create.and.returnValue(of({ id: 2, name: 'New' } as FilterGroup))
      filterGroupService.update.and.returnValue(of({ id: 1, name: 'Saved' } as FilterGroup))
      const selector = Object.create(FilterGroupSelectorComponent.prototype) as FilterGroupSelectorComponent
      Object.assign(selector, {
        _dialog: { open: () => ({ afterClosed: () => of('New') }) },
        _filterGroupService: filterGroupService,
        _snackBar: { success: () => undefined },
        andLabels: [],
        excludeLabels: [],
        // As the template binds the page's
        filters: component.filters,
        orLabels: [],
        orgId: 1,
        selectedFilterGroup: { id: 1, name: 'Saved' },
      })

      selector.saveFilterGroup()
      selector.newFilterGroup()

      expect(filterGroupService.update).toHaveBeenCalledOnceWith(1, 1, jasmine.objectContaining({ query_dict: savedFilters }))
      expect(filterGroupService.create).toHaveBeenCalledOnceWith(1, jasmine.objectContaining({ query_dict: savedFilters }))
    })

    it("shows them on the columns a load adds, e.g., a new profile's", () => {
      const gridApi = jasmine.createSpyObj<GridApi>('GridApi', ['setFilterModel'])
      const inventoryService = jasmine.createSpyObj<InventoryService>('InventoryService', ['getAgInventory'])
      // With the column outside the previous profile, and without address_line_1_1
      const columnDefs: ColDef[] = [{ field: 'site_eui_2' }, { field: 'removed_column_3' }]
      inventoryService.getAgInventory.and.callFake(() => of({ results: [], column_defs: structuredClone(columnDefs) }))
      Object.assign(component, {
        _injector: TestBed.inject(Injector),
        _inventoryService: inventoryService,
        _withLoadingOverlay: withLoadingOverlay(() => undefined),
        appliedLabels: [],
        chunk: 100,
        cycle: { organization: 1 },
        cycleId: 2,
        gridApi,
        labelSelections: { andLabels: [], orLabels: [], excludeLabels: [] },
        orgId: 1,
      })
      const load = () => {
        component.loadInventory().subscribe()
        TestBed.tick()
      }

      load()
      expect(component.columnDefs.map(({ sort }) => sort)).toEqual(['asc', 'desc'])
      expect(gridApi.setFilterModel).toHaveBeenCalledOnceWith({ Building: filters.Building, removed_column_3: hiddenFilters.removed_column_3 })
      // As the grid then reports them, having dropped address_line_1_1's filter with its column
      component.onGridFilterSortChange({ filters: gridApi.setFilterModel.calls.mostRecent().args[0], sorts: ['site_eui_2', '-removed_column_3'] })
      expect(refresh).not.toHaveBeenCalled()
      expect(component.userSettings).toEqual({ filters: { properties: savedFilters }, sorts: { properties: savedSorts } })

      // Not on loads with the same columns, whose filters the grid keeps
      load()
      expect(gridApi.setFilterModel).toHaveBeenCalledTimes(1)

      // But on the first load, even without API columns (e.g., for the access level columns' filters)
      component.columnDefs = []
      inventoryService.getAgInventory.and.returnValue(of({ results: [], column_defs: [] }))
      load()
      expect(gridApi.setFilterModel).toHaveBeenCalledWith({ Building: filters.Building })
    })
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
