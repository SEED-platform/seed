import { TestBed } from '@angular/core/testing'
import { Router } from '@angular/router'
import { TranslocoService } from '@jsverse/transloco'
import type { ColDef, GridApi } from 'ag-grid-community'
import { BehaviorSubject, of, Subject, throwError } from 'rxjs'
import type { Column, CurrentUser, Cycle, Organization, OrganizationUserResponse } from '@seed/api'
import { ColumnService, CycleService, InventoryService, OrganizationService, UserService } from '@seed/api'
import { ConfigService } from '@seed/services'
import type { CrossCyclesResponse } from 'app/modules/inventory/inventory.types'
import { CrossCyclesGridComponent } from './cross-cycles-grid.component'

describe('CrossCyclesGridComponent', () => {
  let component: CrossCyclesGridComponent
  let filterPresent: boolean
  let sortActive: boolean
  let saveSucceeds: boolean
  let filterByCycle: jasmine.Spy
  let cycleService: { cycles$: BehaviorSubject<Cycle[]> }
  let userService: { currentUser$: unknown }
  let getAgInventory: jasmine.Spy

  // Cycle ids deliberately out of start-date order
  const cycles = [
    { id: 1, name: '2023', start: '2023-01-01', organization: 1 },
    { id: 2, name: '2022', start: '2022-01-01', organization: 1 },
  ] as Cycle[]
  const columns = [
    { id: 5, column_name: 'custom_id_1', name: 'custom_id_1_5', display_name: 'Custom ID 1', data_type: 'string', related: false },
    { id: 9, column_name: 'custom_id_1', name: 'custom_id_1_9', display_name: 'Custom ID 1', data_type: 'string', related: true },
    { id: 56, column_name: 'site_eui', name: 'site_eui_56', display_name: 'Site EUI', data_type: 'eui', related: false },
  ] as Column[]
  const dataByCycle = {
    1: [
      { id: 7, custom_id_1_5: 'A', site_eui_56: null },
      { id: 8, custom_id_1_5: 'B', site_eui_56: 50 },
    ],
    2: [{ id: 7, custom_id_1_5: 'A', site_eui_56: 141.8 }],
  }
  const org = { id: 1, cycles: [1, 2], display_decimal_places: 2 } as unknown as Organization

  beforeEach(() => {
    filterPresent = false
    sortActive = false
    saveSucceeds = true
    filterByCycle = jasmine.createSpy('filterByCycle').and.returnValue(of(dataByCycle))
    // a different row per cycle (requested in selectedCycleIds order: 1, then 2)
    getAgInventory = jasmine
      .createSpy('getAgInventory')
      .and.returnValues(of({ results: [{ id: 7, site_eui_56: 10 }] }), of({ results: [{ id: 7, site_eui_56: 20 }] }))
    cycleService = { cycles$: new BehaviorSubject(cycles) }
    userService = {
      currentUser$: of({ settings: { profile: { list: {} }, crossCycles: { properties: [1, 2] } } } as unknown as CurrentUser),
    }
    TestBed.configureTestingModule({
      providers: [
        { provide: ColumnService, useValue: { propertyColumns$: of(columns) } },
        { provide: CycleService, useValue: cycleService },
        { provide: InventoryService, useValue: { getColumnListProfiles: () => of([]), filterByCycle, getAgInventory } },
        {
          provide: OrganizationService,
          useValue: {
            getMatchingCriteriaColumns: () => of([]),
            updateOrganizationUser: () => (saveSucceeds ? of({}) : throwError(() => new Error('save failed'))),
          },
        },
        { provide: UserService, useValue: userService },
        { provide: Router, useValue: {} },
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: TranslocoService, useValue: { translate: (key: string) => key } },
      ],
    })
    component = TestBed.runInInjectionContext(() => new CrossCyclesGridComponent())
    component.type = 'properties'
    component.gridApi = {
      isDestroyed: () => false,
      isAnyFilterPresent: () => filterPresent,
      getColumnState: () => [{ colId: 'site_eui_56', sort: sortActive ? 'desc' : null }],
      refreshCells: () => undefined,
    } as unknown as GridApi
    component.getDependencies(org).subscribe()
  })

  afterEach(() => {
    component.ngOnDestroy()
  })

  it('builds data columns from this inventory type only, skipping related columns', () => {
    const fields = component.columnDefs.map((c) => c.field)

    expect(fields).toContain('custom_id_1_5')
    expect(fields).toContain('site_eui_56')
    expect(fields).not.toContain('custom_id_1_9')
  })

  it('shows collapsed group rows without field values when no filter is active', () => {
    expect(component.rowData).toEqual([
      { id: 7, _isGroup: true, _cycleCount: 2, cycle_name: '2 cycles', cycle_start: null },
      { id: 8, _isGroup: true, _cycleCount: 1, cycle_name: '1 cycle', cycle_start: null },
    ])
  })

  it('expands a group with its cycle rows in start-date order', () => {
    component.toggleGroup(7)

    expect(component.rowData.map((r) => [r.id, r._isGroup, r.cycle_name])).toEqual([
      [7, true, '2 cycles'],
      [7, false, '2022'],
      [7, false, '2023'],
      [8, true, '1 cycle'],
    ])
  })

  it('shows every cycle row ungrouped while a filter is active, and regroups when it is cleared', () => {
    component.toggleGroup(8)
    filterPresent = true
    component.onFilterOrSortChanged()

    expect(component.rowData.map((r) => [r.id, r.cycle_name, r.site_eui_56])).toEqual([
      [7, '2022', 141.8],
      [7, '2023', null],
      [8, '2023', 50],
    ])

    filterPresent = false
    component.onFilterOrSortChanged()

    expect(component.rowData.map((r) => [r.id, r._isGroup])).toEqual([
      [7, true],
      [8, true],
      [8, false],
    ])
  })

  it('shows latitude and longitude at full precision while rounding other decimals to the org setting', () => {
    for (const [id, column_name] of [[57, 'latitude'], [58, 'longitude']] as const) {
      component.columnMap.set(id, { id, column_name, name: `${column_name}_${id}`, data_type: 'number', related: false } as Column)
      const colDef = component.buildColumnDef({ id, display_name: column_name })
      expect(colDef.valueFormatter).toBeUndefined()
      expect(colDef.filter).toBe('agNumberColumnFilter')
    }

    const formatEui = component.buildColumnDef({ id: 56, display_name: 'Site EUI' }).valueFormatter as (p: { value: number }) => string
    expect(formatEui({ value: 141.8123 })).toBe('141.81')
  })

  // Only catches the bug outside UTC (CI runs in UTC): TZ=America/Denver pnpm ng test
  it('displays and filters date-only values as local calendar dates', () => {
    const jan1 = new Date(2022, 0, 1)
    const formatCycleStart = component.buildCycleStartColumnDef().valueFormatter as (p: { value: string }) => string
    const dateColDef: ColDef = {}
    component.applyDataTypeFormatting(dateColDef, 'date')
    const formatDate = dateColDef.valueFormatter as (p: { value: string }) => string

    expect(formatCycleStart({ value: '2022-01-01' })).toBe(jan1.toLocaleDateString())
    expect(formatDate({ value: '2022-01-01' })).toBe(jan1.toLocaleDateString())
    expect(component.dateComparator(jan1, '2022-01-01')).toBe(0)
    expect(formatDate({ value: '2022-02-30' })).toBe('Invalid Date')
  })

  it('shows every cycle row ungrouped while a sort is active, so cycle rows are not split from their group', () => {
    component.toggleGroup(7)
    sortActive = true
    component.onFilterOrSortChanged()

    expect(component.rowData.every((r) => !r._isGroup)).toBeTrue()
    expect(component.rowData.length).toBe(3)

    sortActive = false
    component.onFilterOrSortChanged()

    expect(component.rowData.map((r) => [r.id, r._isGroup])).toEqual([
      [7, true],
      [7, false],
      [7, false],
      [8, true],
    ])
  })

  it('stays flat while a filter and a sort are both active and only one is cleared', () => {
    filterPresent = true
    sortActive = true
    component.onFilterOrSortChanged()
    filterPresent = false
    component.onFilterOrSortChanged()

    expect(component.rowData.every((r) => !r._isGroup)).toBeTrue()

    filterPresent = true
    sortActive = false
    component.onFilterOrSortChanged()

    expect(component.rowData.every((r) => !r._isGroup)).toBeTrue()
  })

  it('rebuilds grouped rows when the grid was destroyed (e.g. after deselecting every cycle)', () => {
    // A destroyed grid's API stub returns undefined from every method but isDestroyed
    component.gridApi = {
      isDestroyed: () => true,
      isAnyFilterPresent: () => undefined,
      getColumnState: () => undefined,
    } as unknown as GridApi
    component.setGrid().subscribe()

    expect(component.error).toBeFalse()
    expect(component.rowData.map((r) => [r.id, r._isGroup])).toEqual([
      [7, true],
      [8, true],
    ])
  })

  const detailParams = (cycle: string) => ({
    organization_id: '1',
    cycle,
    inventory_type: 'property',
    include_related: 'false',
    per_page: '1',
  })
  const agInventoryCalls = () =>
    (getAgInventory.calls.allArgs() as [string, unknown][]).map(([params, data]) => [Object.fromEntries(new URLSearchParams(params)), data])

  it('in property detail mode, fetches only the linked property, one filter call per cycle', () => {
    filterByCycle.calls.reset()
    component.mode = 'detail'
    component.linkingId = 7
    component.setGrid().subscribe()

    expect(filterByCycle).not.toHaveBeenCalled()
    expect(agInventoryCalls()).toEqual([
      [detailParams('1'), { include_property_ids: [7], profile_id: undefined }],
      [detailParams('2'), { include_property_ids: [7], profile_id: undefined }],
    ])
    expect(component.rowData.map((r) => [r.id, r.cycle_name, r.site_eui_56])).toEqual([
      [7, '2022', 20],
      [7, '2023', 10],
    ])
  })

  it('in property detail mode, sends the selected profile_id', () => {
    component.mode = 'detail'
    component.linkingId = 7
    component.selectedProfileId = 3
    component.setGrid().subscribe()

    expect(agInventoryCalls().map(([, data]) => data)).toEqual([
      { include_property_ids: [7], profile_id: 3 },
      { include_property_ids: [7], profile_id: 3 },
    ])
  })

  it('in property detail mode, shows the error state when any cycle request fails', () => {
    getAgInventory.and.returnValues(
      of({ results: [{ id: 7 }] }),
      throwError(() => new Error('filter failed')),
    )
    component.mode = 'detail'
    component.linkingId = 7
    component.setGrid().subscribe()

    expect(component.error).toBeTrue()
    expect(component.rowData).toEqual([])
  })

  it('in tax lot detail mode, uses filterByCycle and keeps only the linked record', () => {
    filterByCycle.calls.reset()
    component.type = 'taxlots'
    component.mode = 'detail'
    component.linkingId = 7
    component.setGrid().subscribe()

    expect(getAgInventory).not.toHaveBeenCalled()
    expect(filterByCycle).toHaveBeenCalledOnceWith(1, undefined, [1, 2], 'taxlots')
    expect(component.rowData.map((r) => [r.id, r.cycle_name])).toEqual([
      [7, '2022'],
      [7, '2023'],
    ])
  })

  it('saves a new cycle selection and reloads the grid', () => {
    filterByCycle.calls.reset()
    component.selectedCycleIds = [2]
    component.onSelectCycleClosed()

    expect(component.currentUser.settings.crossCycles.properties).toEqual([2])
    expect(filterByCycle).toHaveBeenCalledOnceWith(1, undefined, [2], 'properties')
  })

  it('applies only the latest reload when cycle changes overlap', () => {
    const firstReload$ = new Subject<CrossCyclesResponse>()
    const secondReload$ = new Subject<CrossCyclesResponse>()
    filterByCycle.and.returnValues(firstReload$, secondReload$)
    component.selectedCycleIds = [2]
    component.onSelectCycleClosed()
    component.selectedCycleIds = [1]
    component.onSelectCycleClosed()

    expect(component.loading).toBeTrue()

    secondReload$.next({ 1: [{ id: 8, custom_id_1_5: 'B', site_eui_56: 50 }] })
    secondReload$.complete()
    firstReload$.next({ 2: [{ id: 7, custom_id_1_5: 'A', site_eui_56: 141.8 }] })

    expect(component.rowData.map((r) => r.id)).toEqual([8])
    expect(component.loading).toBeFalse()
  })

  it('reloads the restored profile when the newer of two overlapping saves fails', () => {
    const firstSave$ = new Subject<OrganizationUserResponse>()
    const secondSave$ = new Subject<OrganizationUserResponse>()
    spyOn(TestBed.inject(OrganizationService), 'updateOrganizationUser').and.returnValues(firstSave$, secondSave$)
    filterByCycle.calls.reset()
    component.profiles = [
      { id: 3, columns: [] },
      { id: 4, columns: [] },
    ] as unknown as typeof component.profiles
    component.selectedProfileId = 3
    component.onSelectProfile()
    component.selectedProfileId = 4
    component.onSelectProfile()

    firstSave$.next({} as OrganizationUserResponse)
    firstSave$.complete()
    secondSave$.error(new Error('save failed'))

    expect(component.selectedProfileId).toBe(3)
    expect(component.profile?.id).toBe(3)
    expect(component.currentUser.settings.profile.list.properties).toBe(3)
    expect(filterByCycle).toHaveBeenCalledOnceWith(1, 3, [1, 2], 'properties')
  })

  it('keeps the newer profile when the older of two overlapping saves fails', () => {
    const firstSave$ = new Subject<OrganizationUserResponse>()
    const secondSave$ = new Subject<OrganizationUserResponse>()
    spyOn(TestBed.inject(OrganizationService), 'updateOrganizationUser').and.returnValues(firstSave$, secondSave$)
    filterByCycle.calls.reset()
    component.profiles = [
      { id: 3, columns: [] },
      { id: 4, columns: [] },
    ] as unknown as typeof component.profiles
    component.selectedProfileId = 3
    component.onSelectProfile()
    component.selectedProfileId = 4
    component.onSelectProfile()

    firstSave$.error(new Error('save failed'))
    secondSave$.next({} as OrganizationUserResponse)
    secondSave$.complete()

    expect(component.selectedProfileId).toBe(4)
    expect(component.profile?.id).toBe(4)
    expect(component.currentUser.settings.profile.list.properties).toBe(4)
    expect(filterByCycle).toHaveBeenCalledOnceWith(1, 4, [1, 2], 'properties')
  })

  it('reloads when re-picking a cycle after deselecting them all', () => {
    component.selectedCycleIds = []
    component.onSelectCycleClosed()

    expect(component.rowData).toEqual([])

    filterByCycle.calls.reset()
    component.selectedCycleIds = [1]
    component.onSelectCycleClosed()

    expect(filterByCycle).toHaveBeenCalledOnceWith(1, undefined, [1], 'properties')
  })

  it('skips the save and reload when the cycle selection is unchanged', () => {
    const save = spyOn(TestBed.inject(OrganizationService), 'updateOrganizationUser').and.callThrough()
    filterByCycle.calls.reset()
    component.selectedCycleIds = [2, 1]
    component.onSelectCycleClosed()

    expect(save).not.toHaveBeenCalled()
    expect(filterByCycle).not.toHaveBeenCalled()
  })

  it('skips the save and reload when a first-time user closes the default cycle selection unchanged', () => {
    component.currentUser.settings.crossCycles = {}
    component.getDependencies(org).subscribe()
    const save = spyOn(TestBed.inject(OrganizationService), 'updateOrganizationUser').and.callThrough()
    filterByCycle.calls.reset()
    component.selectedCycleIds = [1]
    component.onSelectCycleClosed()

    expect(save).not.toHaveBeenCalled()
    expect(filterByCycle).not.toHaveBeenCalled()
  })

  it('restores the previous cycle selection and skips the reload when the save fails', () => {
    filterByCycle.calls.reset()
    saveSucceeds = false
    component.selectedCycleIds = [2]
    component.onSelectCycleClosed()

    expect(component.currentUser.settings.crossCycles.properties).toEqual([1, 2])
    expect(component.selectedCycleIds).toEqual([1, 2])
    expect(filterByCycle).not.toHaveBeenCalled()
  })

  it('restores the previous profile when the save fails', () => {
    filterByCycle.calls.reset()
    saveSucceeds = false
    component.profiles = [{ id: 3 }] as typeof component.profiles
    component.selectedProfileId = 3
    component.onSelectProfile()

    expect(component.currentUser.settings.profile.list.properties).toBeUndefined()
    expect(component.selectedProfileId).toBeUndefined()
    expect(component.profile).toBeUndefined()
    expect(filterByCycle).not.toHaveBeenCalled()
  })

  describe('while the cycle list is still loading', () => {
    beforeEach(() => {
      filterByCycle.calls.reset()
      cycleService.cycles$ = new BehaviorSubject<Cycle[]>([])
    })

    it('requests filter_by_cycle once, after the cycles arrive', () => {
      component.getDependencies(org).subscribe()
      cycleService.cycles$.next(cycles)
      cycleService.cycles$.next([...cycles])

      expect(filterByCycle).toHaveBeenCalledOnceWith(1, undefined, [1, 2], 'properties')
    })

    it('defaults to the first cycle without throwing when no cycles were saved', () => {
      userService.currentUser$ = of({ settings: { profile: { list: {} } } } as unknown as CurrentUser)

      const error = jasmine.createSpy('error')
      component.getDependencies(org).subscribe({ error })
      cycleService.cycles$.next(cycles)

      expect(error).not.toHaveBeenCalled()
      expect(filterByCycle).toHaveBeenCalledOnceWith(1, undefined, [1], 'properties')
    })

    it("ignores another org's cycles", () => {
      component.getDependencies(org).subscribe()
      cycleService.cycles$.next([{ ...cycles[0], organization: 2 }])

      expect(filterByCycle).not.toHaveBeenCalled()
    })
  })
})
