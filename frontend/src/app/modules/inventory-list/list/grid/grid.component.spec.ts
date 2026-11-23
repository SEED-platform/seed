import 'app/ag-grid-modules'
import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import { MatIconTestingModule } from '@angular/material/icon/testing'
import { provideRouter } from '@angular/router'
import type { ColDef, FilterModel } from 'ag-grid-community'
import { themeQuartz } from 'ag-grid-community'
import { of } from 'rxjs'
import type { CurrentUser } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { getTranslocoTestingModule } from 'app/core/transloco/transloco-testing'
import type { FiltersSorts, Pagination } from 'app/modules/inventory/inventory.types'
import { InventoryGridComponent, serverFilterColDef } from './grid.component'

describe('serverFilterColDef', () => {
  it('maps each server filter type to its filter', () => {
    expect(serverFilterColDef('text')).toEqual({ cellDataType: 'text', filter: 'agTextColumnFilter' })
    expect(serverFilterColDef('boolean')).toEqual({ cellDataType: 'boolean', filter: 'agTextColumnFilter' })
    expect(serverFilterColDef('number')).toEqual({ cellDataType: false, filter: 'agNumberColumnFilter' })
    expect(serverFilterColDef('date')).toEqual({ cellDataType: false, filter: 'agDateColumnFilter', filterParams: { includeTime: false } })
  })

  it('falls back to a text filter for a missing or unknown filter type', () => {
    for (const filterType of [undefined, '', 'set', 'toString']) {
      expect(serverFilterColDef(filterType)).toEqual(serverFilterColDef('text'))
    }
  })

  it('returns new filter params for each column', () => {
    const { filterParams } = serverFilterColDef('date') as { filterParams: Record<string, unknown> }
    filterParams.includeTime = true
    expect(serverFilterColDef('date').filterParams).toEqual({ includeTime: false })
  })
})

describe('InventoryGridComponent server-side filtering', () => {
  const apiColumnDefs: ColDef[] = [
    { field: 'address_line_1_1', headerName: 'Address Line 1', context: { filterType: 'text' } },
    { field: 'gross_floor_area_2', headerName: 'Gross Floor Area', context: { filterType: 'number' } },
    { field: 'year_ending_3', headerName: 'Year Ending', context: { filterType: 'date' } },
    { field: 'long_lat_4', headerName: 'Longitude Latitude', filter: false },
    { field: 'has_solar_5', headerName: 'Has Solar', context: { filterType: 'boolean' } },
  ]
  // Date-time strings, which AG Grid would otherwise give a time picker, and a number stored as text
  const rowData = [
    { property_view_id: 1, address_line_1_1: '1 Main St', gross_floor_area_2: 1000, year_ending_3: '2020-12-31T10:00:00', Building: 'A' },
    { property_view_id: 2, address_line_1_1: '2 Oak Ave', gross_floor_area_2: '2,500', year_ending_3: '2021-12-31T10:00:00', Building: 'B' },
    { property_view_id: 3, address_line_1_1: '3 Elm Rd', gross_floor_area_2: 4000, year_ending_3: '2022-12-31T10:00:00', Building: 'B' },
  ]
  // Each filter excludes every row, if the grid filtered them itself
  const excludingFilters: FilterModel = {
    address_line_1_1: { filterType: 'text', type: 'contains', filter: 'nowhere' },
    gross_floor_area_2: { filterType: 'number', type: 'greaterThan', filter: 1e9 },
    year_ending_3: { filterType: 'date', type: 'equals', dateFrom: '1900-01-01 00:00:00', dateTo: null },
    Building: { filterType: 'text', type: 'equals', filter: 'nowhere' },
  }
  const pagination: Pagination = { start: 1, end: 3, total: 3, page: 1, num_pages: 1, has_next: false, has_previous: false }

  let fixture: ComponentFixture<InventoryGridComponent>
  let component: InventoryGridComponent

  const floatingFilterInput = (colId: string, selector = 'input') => {
    return (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>(`.ag-floating-filter[col-id="${colId}"] ${selector}`)
  }

  const typeInto = async (input: HTMLInputElement, value: string) => {
    input.value = value
    input.dispatchEvent(new Event('input', { bubbles: true }))
    // Waits for the floating filter's debounce
    await fixture.whenStable()
  }

  const createGrid = async (rows: Record<string, unknown>[]) => {
    await TestBed.configureTestingModule({
      imports: [InventoryGridComponent, MatIconTestingModule, getTranslocoTestingModule()],
      providers: [
        provideRouter([]),
        { provide: ConfigService, useValue: { gridTheme$: of(themeQuartz), scheme$: of('light') } },
        { provide: OrganizationService, useValue: {} },
      ],
    }).compileComponents()

    fixture = TestBed.createComponent(InventoryGridComponent)
    component = fixture.componentInstance
    // Wide enough to render every column's floating filter
    const host = fixture.nativeElement as HTMLElement
    host.style.width = '2500px'
    const inputs = {
      accessLevelNames: ['Root', 'Building'],
      columnDefs: apiColumnDefs,
      currentUser: { org_id: 1, org_user_id: 2, settings: {} } as CurrentUser,
      inventoryType: 'properties',
      labelMap: {},
      pagination,
      rowData: rows,
      selectedViewIds: [],
      type: 'properties',
      userSettings: {},
    }
    for (const [name, value] of Object.entries(inputs)) {
      fixture.componentRef.setInput(name, value)
    }
    fixture.detectChanges()
    await fixture.whenStable()
  }

  beforeEach(async () => {
    await createGrid(rowData)
  })

  it('only offers the filters the server supports', () => {
    expect(component.columnDefs.some(({ filter }) => filter === true)).toBeFalse()

    const columns = component.gridApi.getColumns()
    expect(columns.some((column) => column.getColDef().filter === true)).toBeFalse()
    expect(columns.filter((column) => column.isFilterAllowed()).map((column) => column.getColId())).toEqual([
      'Building',
      'address_line_1_1',
      'gross_floor_area_2',
      'year_ending_3',
      'has_solar_5',
    ])
  })

  it('keeps every row the server returned, including after new rows arrive', async () => {
    component.gridApi.setFilterModel(excludingFilters)
    await fixture.whenStable()

    expect(component.gridApi.isColumnFilterPresent()).toBeTrue()
    expect(component.gridApi.getFilterModel()).toEqual(excludingFilters)
    expect(component.gridApi.getDisplayedRowCount()).toBe(rowData.length)

    // A new page rebuilds the column defs
    fixture.componentRef.setInput('rowData', rowData.map((row) => ({ ...row })))
    fixture.detectChanges()
    await fixture.whenStable()

    expect(component.gridApi.getFilterModel()).toEqual(excludingFilters)
    expect(component.gridApi.getDisplayedRowCount()).toBe(rowData.length)
  })

  it('builds the server filter model from each floating filter', async () => {
    let emitted: FiltersSorts
    component.filterSortChange.subscribe((filtersSorts) => (emitted = filtersSorts))

    await typeInto(floatingFilterInput('address_line_1_1'), 'nowhere')
    await typeInto(floatingFilterInput('Building'), 'nowhere')
    await typeInto(floatingFilterInput('gross_floor_area_2', 'input[type="number"]'), '1000000000')
    const dateInput = floatingFilterInput('year_ending_3', '.ag-date-floating-filter-wrapper input')
    expect(dateInput.type).toBe('date')
    await typeInto(dateInput, '1900-01-01')

    const expected = {
      address_line_1_1: { filterType: 'text', type: 'contains', filter: 'nowhere' },
      Building: { filterType: 'text', type: 'contains', filter: 'nowhere' },
      gross_floor_area_2: { filterType: 'number', type: 'equals', filter: 1e9 },
      year_ending_3: { filterType: 'date', type: 'equals', dateFrom: '1900-01-01 00:00:00', dateTo: null },
    }
    expect(component.gridApi.getFilterModel()).toEqual(expected)
    expect(emitted.filters).toEqual(expected)
    expect(component.gridApi.getDisplayedRowCount()).toBe(rowData.length)
  })

  it('shows a saved date filter in its date-only floating filter', async () => {
    component.gridApi.setFilterModel({ year_ending_3: excludingFilters.year_ending_3 as object })
    await fixture.whenStable()

    expect(floatingFilterInput('year_ending_3', '.ag-date-floating-filter-wrapper input').value).toBe('1900-01-01')
  })

  it('shows the values the server filters on', () => {
    const values: unknown[] = []
    component.gridApi.forEachNode((rowNode) => {
      values.push(component.gridApi.getCellValue({ rowNode, colKey: 'gross_floor_area_2', useFormatter: true }))
    })
    expect(values).toEqual(['1000', '2,500', '4000'])
  })

  it('restores filters before it has rows', async () => {
    // e.g., saved filters that the cycle's inventory doesn't match
    TestBed.resetTestingModule()
    await createGrid([])
    component.gridApi.setFilterModel(excludingFilters)
    await fixture.whenStable()

    expect(component.gridApi.getFilterModel()).toEqual(excludingFilters)
  })
})
