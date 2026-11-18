import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { Router } from '@angular/router'
import { TranslocoDirective, TranslocoService } from '@jsverse/transloco'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridOptions, GridReadyEvent } from 'ag-grid-community'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { catchError, combineLatest, EMPTY, filter, finalize, forkJoin, map, of, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { Column, CurrentUser, Cycle, Organization } from '@seed/api'
import { ColumnService, CycleService, InventoryService, OrganizationService, UserService } from '@seed/api'
import { NotFoundComponent } from '@seed/components'
import { buildFilterChips, FilterChipsComponent, removeGridFilter } from '@seed/components/filter-chips'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import type { CrossCyclesResponse, FilterSortChip, InventoryDisplayType, InventoryType, Profile } from 'app/modules/inventory/inventory.types'

ModuleRegistry.registerModules([AllCommunityModule])

const NUMERIC_DATA_TYPES = new Set<Column['data_type']>([
  'number',
  'float',
  'integer',
  'area',
  'eui',
  'ghg',
  'ghg_intensity',
  'wui',
  'water_use',
])
const DECIMAL_DATA_TYPES = new Set<Column['data_type']>(['number', 'float', 'area', 'eui'])
// Coordinates keep full precision instead of the org's display_decimal_places
const UNROUNDED_COLUMN_NAMES = new Set(['latitude', 'longitude'])

// new Date('YYYY-MM-DD') is UTC midnight (the previous day in US time zones), so read date-only strings as local dates
const parseDate = (value: string): Date => {
  const [, y, m, d] = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value) ?? []
  if (!y) return new Date(value)
  const date = new Date(+y, +m - 1, +d)
  // Reject impossible dates like 2022-02-30 instead of rolling them over to another day
  return date.getMonth() === +m - 1 ? date : new Date(NaN)
}

@Component({
  selector: 'seed-cross-cycles-grid',
  templateUrl: './cross-cycles-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, FilterChipsComponent, MaterialImports, NotFoundComponent, TranslocoDirective],
})
export class CrossCyclesGridComponent implements OnChanges, OnDestroy {
  @Input({ required: true }) type!: InventoryType
  @Input() mode: 'list' | 'detail' = 'list'
  @Input() linkingId?: number
  private _columnService = inject(ColumnService)
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _inventoryService = inject(InventoryService)
  private _organizationService = inject(OrganizationService)
  private _router = inject(Router)
  private _transloco = inject(TranslocoService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private readonly _reload$ = new Subject<void>()
  // shortcut: a save that never settles blocks later reloads, add a timeout if hung saves are seen
  private _pendingSaves = 0
  private _loadedCycleIds: number[] = []
  private _savedSinceReload = false
  private _detailRowsByLinkingId = new Map<number, Record<string, unknown>[]>()
  private _expandedLinkingIds = new Set<number>()
  private _showingFlatRows = false
  columnDefs: ColDef[] = []
  columnMap = new Map<number, Column>()
  columns: Column[] = []
  currentUser: CurrentUser
  cycles: Cycle[] = []
  displayType: InventoryDisplayType
  error = false
  filterChips: FilterSortChip[] = []
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  loading = false
  matchingColumns = new Set<string>()
  org: Organization
  orgId: number
  profile?: Profile
  profiles: Profile[] = []
  rowData: Record<string, unknown>[] = []
  selectedCycleIds: number[] = []
  selectedProfileId?: number

  gridOptions: GridOptions<Record<string, unknown>> = {
    getRowStyle: (params) => {
      if (params.data?._isGroup) {
        return { fontWeight: '600', borderTop: '2px solid var(--ag-row-border-color)' }
      }
      return undefined
    },
  }

  defaultColDef = {
    sortable: true,
    filter: true,
    floatingFilter: true,
    resizable: true,
    minWidth: 75,
  }

  constructor() {
    // Lives outside initPage's subscriptions; switchMap drops an older reload so its response can't overwrite a newer one
    this._reload$
      .pipe(
        switchMap(() => this.setGrid()),
        takeUntilDestroyed(),
      )
      .subscribe()
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.type || changes.mode || changes.linkingId) {
      this.displayType = this.type === 'taxlots' ? 'Tax Lot' : 'Property'
      this.initPage()
    }
  }

  initPage(): void {
    // Cancel any prior initPage() subscriptions (e.g. when inputs change)
    this._unsubscribeAll$.next()

    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap((org) => this.getDependencies(org)),
      )
      .subscribe()
  }

  getDependencies(org: Organization): Observable<unknown> {
    this.org = org
    this.orgId = org.id
    // Clear the previous org's grid so it doesn't linger while this org's cycles load
    this.cycles = []
    this.rowData = []

    if (!org.cycles.length) {
      return EMPTY
    }

    const columns$ = this.type === 'properties' ? this._columnService.propertyColumns$ : this._columnService.taxLotColumns$

    return combineLatest([
      this._userService.currentUser$,
      // CycleService loads cycles on org change; wait for this org's list once instead of refetching
      this._cycleService.cycles$.pipe(
        filter((cycles) => cycles[0]?.organization === this.orgId),
        take(1),
      ),
      this._inventoryService.getColumnListProfiles('List View Profile', this.type),
      this._organizationService.getMatchingCriteriaColumns(this.orgId, this.type),
      columns$,
    ]).pipe(
      takeUntil(this._unsubscribeAll$),
      tap(([currentUser, cycles, profiles, matchingColumns, columns]: [CurrentUser, Cycle[], Profile[], string[], Column[]]) => {
        this.currentUser = currentUser
        this.cycles = cycles
        // filter_by_cycle only returns this inventory type's own columns, not related (e.g. tax lot) ones
        this.columns = columns.filter((c) => !c.related)
        this.columnMap = new Map(this.columns.map((c) => [c.id, c]))
        this.matchingColumns = new Set(matchingColumns)
        this.profiles = profiles
          .filter((p) => p.inventory_type === this.displayType && p.profile_location === 'List View Profile')
          .sort((a, b) => naturalSort(a.name, b.name))

        this.ensureUserSettingsDefaults()
        this.selectedProfileId = this.currentUser.settings.profile.list[this.type]
        this.profile = this.profiles.find((p) => p.id === this.selectedProfileId)
        this.selectedCycleIds = this.getSelectedCycleIds()
      }),
      switchMap(() => this.setGrid()),
    )
  }

  /*
   * Guard against org users who have never saved cross-cycles/profile settings before -
   * `settings` is a bare JSON blob on the backend with no guaranteed default shape.
   */
  ensureUserSettingsDefaults(): void {
    this.currentUser.settings.profile ??= {}
    this.currentUser.settings.profile.list ??= {}
    this.currentUser.settings.crossCycles ??= {}
  }

  getSelectedCycleIds(): number[] {
    if (this.mode === 'detail') {
      return this.cycles.map((c) => c.id)
    }
    return this.currentUser.settings.crossCycles[this.type]?.length ? this.currentUser.settings.crossCycles[this.type] : [this.cycles[0].id]
  }

  setGrid(): Observable<unknown> {
    this._loadedCycleIds = this.selectedCycleIds
    if (!this.selectedCycleIds.length) {
      this.rowData = []
      this.columnDefs = []
      return EMPTY
    }

    this.loading = true
    this.error = false
    return this.getDataByCycle().pipe(
      tap((dataByCycle) => {
        this.setColumnDefs()
        this.setRowData(dataByCycle)
      }),
      catchError(() => {
        this.error = true
        this.rowData = []
        return of(null)
      }),
      finalize(() => {
        this.loading = false
      }),
    )
  }

  getDataByCycle(): Observable<CrossCyclesResponse> {
    // shortcut: the v4 filter has include_property_ids but no tax lot equivalent, so tax lots load the whole org until it gets one
    if (this.mode === 'detail' && this.type === 'properties') return this.getPropertyDataByCycle()
    return this._inventoryService.filterByCycle(this.orgId, this.selectedProfileId, this.selectedCycleIds, this.type)
  }

  // Fetch only this property, one filter call per cycle, instead of filter_by_cycle serializing every record in the org
  getPropertyDataByCycle(): Observable<CrossCyclesResponse> {
    return forkJoin(this.selectedCycleIds.map((cycleId) => this.getPropertyRows(cycleId))).pipe(
      map((entries) => Object.fromEntries(entries)),
    )
  }

  getPropertyRows(cycleId: number): Observable<[number, Record<string, unknown>[]]> {
    const params = new URLSearchParams({
      organization_id: this.orgId.toString(),
      cycle: cycleId.toString(),
      inventory_type: 'property',
      include_related: 'false',
      // a property has at most one view per cycle
      per_page: '1',
    })
    const data = { include_property_ids: [this.linkingId], profile_id: this.selectedProfileId }
    return this._inventoryService
      .getAgInventory(params.toString(), data)
      .pipe(map(({ results }) => [cycleId, results as Record<string, unknown>[]]))
  }

  setColumnDefs(): void {
    const dataColumns = this.profile
      ? [...this.profile.columns].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)).map((c) => this.buildColumnDef(c))
      : this.columns.filter((c) => !c.is_extra_data).map((c) => this.buildColumnDef(c))

    this.columnDefs = [
      ...(this.mode === 'list' ? [this.buildExpandColumnDef()] : []),
      this.buildLinkingIdColumnDef(),
      this.buildDetailLinkColumnDef(),
      this.buildCycleColumnDef(),
      this.buildCycleStartColumnDef(),
      ...dataColumns.filter((c): c is ColDef => Boolean(c)),
    ]
  }

  buildColumnDef({ id, display_name, pinned = false }: { id: number; display_name: string; pinned?: boolean }): ColDef | null {
    const column = this.columnMap.get(id)
    if (!column) return null

    const isMatching = this.matchingColumns.has(column.column_name)
    const colDef: ColDef = {
      field: column.name,
      headerName: isMatching ? `${display_name}*` : display_name,
      headerTooltip: isMatching ? this._transloco.translate('Matching criteria columns are given sort priority') : display_name,
      pinned: isMatching || pinned ? 'left' : null,
      width: 150,
    }

    this.applyDataTypeFormatting(colDef, column.data_type, column.column_name)
    return colDef
  }

  buildLinkingIdColumnDef(): ColDef {
    return {
      field: 'id',
      headerName: this._transloco.translate('Linking ID'),
      pinned: 'left',
      hide: this.mode === 'detail',
      ...(this.mode === 'detail' ? { sort: 'asc' as const, sortIndex: 0 } : {}),
      width: 110,
    }
  }

  buildDetailLinkColumnDef(): ColDef {
    const field = this.type === 'taxlots' ? 'taxlot_view_id' : 'property_view_id'
    const detailLabel = this._transloco.translate('View detail')

    return {
      field,
      headerName: '',
      pinned: 'left',
      width: 44,
      maxWidth: 44,
      sortable: false,
      filter: false,
      floatingFilter: false,
      suppressMovable: true,
      cellRenderer: ({ data, value }: { data: Record<string, unknown>; value: number }) =>
        !data._isGroup && value
          ? `<button type="button" class="mt-2 flex w-full cursor-pointer justify-center" data-action="detail" title="${detailLabel}" aria-label="${detailLabel}"><span class="material-icons-outlined">info</span></button>`
          : '',
    }
  }

  buildCycleColumnDef(): ColDef {
    return {
      field: 'cycle_name',
      headerName: this._transloco.translate('Cycle'),
      pinned: 'left',
      width: 130,
    }
  }

  buildCycleStartColumnDef(): ColDef {
    return {
      field: 'cycle_start',
      headerName: this._transloco.translate('Cycle Start'),
      pinned: 'left',
      filter: 'agDateColumnFilter',
      filterParams: { comparator: this.dateComparator },
      ...(this.mode === 'detail' ? { sort: 'asc' as const, sortIndex: 0 } : {}),
      valueFormatter: ({ value }: { value: string }) => (value ? parseDate(value).toLocaleDateString() : ''),
      width: 130,
    }
  }

  buildExpandColumnDef(): ColDef {
    const toggleLabel = this._transloco.translate('Toggle cycles')
    return {
      colId: 'expand_col',
      headerName: '',
      pinned: 'left',
      width: 36,
      maxWidth: 36,
      sortable: false,
      filter: false,
      floatingFilter: false,
      suppressMovable: true,
      cellRenderer: ({ data }: { data: Record<string, unknown> }) => {
        if (!data?._isGroup) return ''
        const icon = this._expandedLinkingIds.has(data.id as number) ? 'expand_more' : 'chevron_right'
        return `<button type="button" class="mt-2 flex w-full cursor-pointer justify-center" data-action="toggle" aria-label="${toggleLabel}"><span class="material-icons-outlined">${icon}</span></button>`
      },
    }
  }

  applyDataTypeFormatting(colDef: ColDef, dataType?: Column['data_type'], columnName?: string): void {
    if (dataType === 'datetime' || dataType === 'date') {
      colDef.filter = 'agDateColumnFilter'
      colDef.filterParams = { comparator: this.dateComparator }
      colDef.valueFormatter = ({ value }: { value: string }) => {
        if (!value) return ''
        return dataType === 'date' ? parseDate(value).toLocaleDateString() : parseDate(value).toLocaleString()
      }
      return
    }
    if (dataType === 'boolean') {
      colDef.valueFormatter = ({ value }: { value: boolean }) => (value === true ? 'true' : value === false ? 'false' : '')
      return
    }
    if (dataType && NUMERIC_DATA_TYPES.has(dataType)) {
      colDef.filter = 'agNumberColumnFilter'
      if (DECIMAL_DATA_TYPES.has(dataType) && !UNROUNDED_COLUMN_NAMES.has(columnName)) {
        colDef.valueFormatter = ({ value }: { value: number }) =>
          typeof value === 'number' ? value.toFixed(this.org.display_decimal_places) : ''
      }
    }
  }

  dateComparator = (filterDate: Date, cellValue: string): number => {
    if (!cellValue) return -1
    const cellDate = parseDate(cellValue)
    if (cellDate < filterDate) return -1
    if (cellDate > filterDate) return 1
    return 0
  }

  setRowData(dataByCycle: CrossCyclesResponse): void {
    const cycleById = new Map(this.cycles.map((c) => [c.id, c]))
    const allDetailRows: Record<string, unknown>[] = Object.entries(dataByCycle ?? {})
      .flatMap<Record<string, unknown>>(([cycleId, records]) =>
        records.map((record) => ({
          ...record,
          _isGroup: false,
          cycle_name: cycleById.get(Number(cycleId))?.name ?? '',
          cycle_start: cycleById.get(Number(cycleId))?.start ?? null,
        })),
      )
      .sort(
        (a, b) => (a.id as number) - (b.id as number) || ((a.cycle_start as string) ?? '').localeCompare((b.cycle_start as string) ?? ''),
      )

    if (this.mode === 'detail' && this.linkingId) {
      this.rowData = allDetailRows.filter((row) => row.id === this.linkingId)
      return
    }

    // Group by linking ID (rows are already sorted); start all collapsed
    this._detailRowsByLinkingId = new Map<number, Record<string, unknown>[]>()
    this._expandedLinkingIds = new Set<number>()

    for (const row of allDetailRows) {
      const id = row.id as number
      const existing = this._detailRowsByLinkingId.get(id) ?? []
      existing.push(row)
      this._detailRowsByLinkingId.set(id, existing)
    }

    this.rowData = this.buildRows()
  }

  /*
   * Group rows carry no field values, so a column filter would hide every group and a sort would
   * split cycle rows from their group. While any filter or sort is active, show the cycle rows
   * ungrouped so they filter and sort on real per-cycle values.
   */
  buildRows(): Record<string, unknown>[] {
    const groups = [...this._detailRowsByLinkingId.entries()]
    this._showingFlatRows = this.shouldShowFlatRows()
    if (this._showingFlatRows) {
      return groups.flatMap(([, detailRows]) => detailRows)
    }

    return groups.flatMap(([id, detailRows]) => [
      this.buildGroupRow(id, detailRows.length),
      ...(this._expandedLinkingIds.has(id) ? detailRows : []),
    ])
  }

  buildGroupRow(id: number, count: number): Record<string, unknown> {
    return {
      id,
      _isGroup: true,
      _cycleCount: count,
      cycle_name: `${count} ${count === 1 ? this._transloco.translate('cycle') : this._transloco.translate('cycles')}`,
      cycle_start: null,
    }
  }

  toggleGroup(linkingId: number): void {
    if (this._expandedLinkingIds.has(linkingId)) {
      this._expandedLinkingIds.delete(linkingId)
    } else {
      this._expandedLinkingIds.add(linkingId)
    }
    this.rowData = this.buildRows()
    this.gridApi?.refreshCells({ columns: ['expand_col'], force: true })
  }

  shouldShowFlatRows(): boolean {
    // The template removes the grid when there are no rows, leaving gridApi pointing at a destroyed grid
    if (!this.gridApi || this.gridApi.isDestroyed()) return false
    return this.gridApi.isAnyFilterPresent() || this.gridApi.getColumnState().some((c) => c.sort)
  }

  onFilterOrSortChanged(): void {
    // Fires on every keystroke; only rebuild when switching between grouped and flat rows
    if (this.mode !== 'list' || this.shouldShowFlatRows() === this._showingFlatRows) return
    this.rowData = this.buildRows()
  }

  onGridReady(params: GridReadyEvent): void {
    this.gridApi = params.api
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
    this.setFilterChips()
  }

  /* Rebuilds the filter badges; also runs when filters or the column set (e.g. a new profile) change */
  setFilterChips(): void {
    if (!this.gridApi || this.gridApi.isDestroyed()) {
      this.filterChips = []
      return
    }
    this.filterChips = buildFilterChips({ filterModel: this.gridApi.getFilterModel(), columnDefs: this.columnDefs })
  }

  onRemoveFilter(chip: FilterSortChip): void {
    removeGridFilter(this.gridApi, chip.original)
  }

  onCellClicked(event: CellClickedEvent): void {
    const action = (event.event?.target as HTMLElement | null)?.closest?.('[data-action]')?.getAttribute('data-action')

    if (action === 'toggle') {
      this.toggleGroup((event.data as Record<string, unknown>).id as number)
      return
    }

    const field = this.type === 'taxlots' ? 'taxlot_view_id' : 'property_view_id'
    if (event.colDef.field !== field) return
    if (action !== 'detail') return

    const { property_view_id, taxlot_view_id } = event.data as { property_view_id?: number; taxlot_view_id?: number }
    const viewId = this.type === 'taxlots' ? taxlot_view_id : property_view_id
    if (viewId) void this._router.navigate([`/${this.type}`, viewId])
  }

  onClearFilters(): void {
    this.gridApi?.setFilterModel(null)
  }

  onSelectCycleClosed(): void {
    const cycleIds = this.selectedCycleIds
    const loaded = this._loadedCycleIds
    if (!this._pendingSaves && loaded.length === cycleIds.length && loaded.every((id) => cycleIds.includes(id))) return

    const previousCycleIds = this.currentUser.settings.crossCycles[this.type]
    this.currentUser.settings.crossCycles[this.type] = cycleIds
    this.saveSettingsAndReload(() => {
      if (this.currentUser.settings.crossCycles[this.type] !== cycleIds) return
      this.currentUser.settings.crossCycles[this.type] = previousCycleIds
      this.selectedCycleIds = this.getSelectedCycleIds()
    })
  }

  onSelectProfile(): void {
    const profileId = this.selectedProfileId
    const previousProfileId = this.currentUser.settings.profile.list[this.type]
    this.currentUser.settings.profile.list[this.type] = profileId
    this.profile = this.profiles.find((p) => p.id === profileId)
    this.saveSettingsAndReload(() => {
      if (this.currentUser.settings.profile.list[this.type] !== profileId) return
      this.currentUser.settings.profile.list[this.type] = previousProfileId
      this.selectedProfileId = previousProfileId
      this.profile = this.profiles.find((p) => p.id === previousProfileId)
    })
  }

  /*
   * currentUser.settings is shared app-wide and is changed before saving, so a failed save must undo
   * that change (the service already reports the error) and leave the grid on its current data.
   * An undo is skipped once a newer change has replaced the value, and the grid reloads once all
   * overlapping saves settle. If an older and then a newer save both fail, the newer undo restores the
   * older, never-saved value.
   */
  saveSettingsAndReload(undoChange: () => void): void {
    this._pendingSaves++
    this.updateOrgUserSettings()
      .pipe(
        tap(() => (this._savedSinceReload = true)),
        catchError(() => {
          undoChange()
          return EMPTY
        }),
        finalize(() => {
          if (--this._pendingSaves || !this._savedSinceReload) return
          this._savedSinceReload = false
          this._reload$.next()
        }),
      )
      .subscribe()
  }

  updateOrgUserSettings() {
    return this._organizationService.updateOrganizationUser(this.currentUser.org_user_id, this.orgId, this.currentUser.settings)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
