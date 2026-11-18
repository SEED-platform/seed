import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, HostListener, inject } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, GridApi, GridReadyEvent, TextMatcherParams } from 'ag-grid-community'
import { catchError, EMPTY, of, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Column } from '@seed/api/column'
import { ColumnService } from '@seed/api/column'
import type { OrgCycle } from '@seed/api/organization'
import { OrganizationService } from '@seed/api/organization'
import type { PropertyColumnStats, PropertyColumnSummary, PropertyColumnSummaryResponse } from '@seed/api/property'
import { PropertyService } from '@seed/api/property'
import { type CurrentUser, UserService } from '@seed/api/user'
import { NotFoundComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

type SummaryGridRow = {
  row_id: string;
  column_name: string;
  display_name: string;
  cycle_id: number;
  cycle_name: string;
  is_extra_data: boolean;
} & Partial<Record<keyof PropertyColumnStats, number | string | boolean | null>>

type CellRendererParams = { value: string; data: SummaryGridRow }

type StatColumnConfig = {
  key: StatKey;
  label: string;
}

type StatKey = Extract<keyof PropertyColumnStats, string>

const STAT_COLUMN_CONFIGS: StatColumnConfig[] = [
  { key: 'non_null_count', label: 'Non-null Count' },
  { key: 'null_count', label: 'Null Count' },
  { key: 'blank_count', label: 'Blank Count' },
  { key: 'min', label: 'Min' },
  { key: 'p05', label: 'P05' },
  { key: 'p25', label: 'P25' },
  { key: 'median', label: 'Median' },
  { key: 'avg', label: 'Average' },
  { key: 'p75', label: 'P75' },
  { key: 'p95', label: 'P95' },
  { key: 'max', label: 'Max' },
  { key: 'stddev', label: 'Std Dev' },
  { key: 'sum', label: 'Sum' },
  { key: 'mode', label: 'Mode' },
  { key: 'distinct_count', label: 'Distinct Count' },
  { key: 'unique_count', label: 'Unique Count' },
  { key: 'uniqueness_ratio', label: 'Uniqueness Ratio' },
]

@Component({
  selector: 'seed-inventory-list-summary',
  templateUrl: './summary.component.html',
  styles: [
    `
      :host ::ng-deep .summary-grid .ag-row {
        cursor: pointer;
      }

      :host ::ng-deep .summary-grid .ag-row.ag-row-selected {
        background-color: rgb(219 234 254);
      }

      :host ::ng-deep .summary-grid .ag-row.ag-row-selected .ag-cell {
        background-color: transparent;
      }

      :host-context(.dark) ::ng-deep .summary-grid .ag-row.ag-row-selected {
        background-color: rgb(30 64 175 / 0.35);
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, NotFoundComponent, PageComponent],
})
export class SummaryComponent implements OnDestroy, OnInit {
  private _columnService = inject(ColumnService)
  private _configService = inject(ConfigService)
  private _organizationService = inject(OrganizationService)
  private _propertyService = inject(PropertyService)
  private _userService = inject(UserService)
  private _route = inject(ActivatedRoute)
  private readonly _unsubscribeAll$ = new Subject<void>()

  availableColumns: Pick<PropertyColumnSummary, 'column_name' | 'display_name' | 'is_extra_data'>[] = []
  availableStatColumns = STAT_COLUMN_CONFIGS
  columnDefs: ColDef[] = []
  currentUser: CurrentUser
  cycles: OrgCycle[] = []
  defaultColDef = {
    suppressMovable: true,
    sortable: true,
    filter: 'agTextColumnFilter',
    floatingFilter: true,
    resizable: true,
    filterParams: {
      suppressAndOrCondition: true,
      textMatcher: (params: TextMatcherParams) => this._matchesFilterExpression(params),
    },
  }
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  rowSelection = {
    mode: 'multiRow' as const,
    checkboxes: false,
    headerCheckbox: false,
    enableClickSelection: true,
  }
  suppressContextMenu = true
  orgId: number
  fullRowData: SummaryGridRow[] = []
  rowData: SummaryGridRow[] = []
  selectedRowIds = new Set<string>()
  selectedRowsOnly = false
  cyclePickerOpen = false
  columnPickerOpen = false
  columnPickerShowSelectedOnly = false
  statPickerOpen = false
  pendingCycleIds: number[] = []
  pendingColumnNames: string[] = []
  pendingStatKeys: StatKey[] = []
  hasSavedColumnSelection = false
  hasSavedCycleSelection = false
  hasSavedStatSelection = false
  selectedColumnNames: string[] = []
  columnSearchTerm = ''
  selectedCycleIds: number[] = []
  selectedStatKeys: StatKey[] = ['non_null_count']
  summary?: PropertyColumnSummaryResponse
  type = this._route.snapshot.paramMap.get('type') as InventoryType
  totalRecords = '0'
  totalExtraData = '0'
  contextMenuVisible = false
  contextMenuX = 0
  contextMenuY = 0
  contextMenuMode: 'field' | 'stat' | null = null
  contextMenuField: Pick<SummaryGridRow, 'column_name' | 'display_name'> | null = null
  contextMenuStatKey: StatKey | null = null
  private _numberFormatter = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 6,
  })

  @HostListener('document:click')
  onDocumentClick() {
    if (this.contextMenuVisible) {
      this.closeContextMenu()
    }
  }

  ngOnInit() {
    this.initPage().pipe(takeUntil(this._unsubscribeAll$)).subscribe()
  }

  initPage() {
    return this._userService.currentUser$.pipe(
      switchMap((user) => this.getDependencies(user)),
      tap(() => {
        this.setGrid()
      }),
    )
  }

  getDependencies(user: CurrentUser) {
    this.currentUser = user
    this.orgId = user.org_id
    return this._organizationService.getById(this.orgId).pipe(
      tap((org) => {
        this.cycles = org.cycles
        const validCycleIds = new Set(org.cycles.map((cycle) => cycle.cycle_id))
        this.hasSavedCycleSelection = Array.isArray(this.currentUser.settings.summaryCycleIds)
        const savedCycleIds = this._getSavedNumberArray('summaryCycleIds').filter((id) => validCycleIds.has(id))
        const defaultCycleIds = org.cycles.slice(-3).map((cycle) => cycle.cycle_id)
        this.selectedCycleIds = this.hasSavedCycleSelection ? savedCycleIds : defaultCycleIds

        const availableStatKeys = new Set(STAT_COLUMN_CONFIGS.map((config) => config.key))
        this.hasSavedStatSelection = Array.isArray(this.currentUser.settings.summaryStatColumns)
        const savedStatKeys = this._getSavedStatKeys(availableStatKeys)
        this.selectedStatKeys = this.hasSavedStatSelection ? savedStatKeys : ['non_null_count']

        if (!this.selectedCycleIds.length && org.cycles.length && !this.hasSavedCycleSelection) {
          this.selectedCycleIds = [org.cycles[0].cycle_id]
        }
      }),
      switchMap(() =>
        this._columnService.getPropertyColumns(this.orgId).pipe(
          tap((columns) => {
            this.setAvailableColumnsFromColumns(columns)
          }),
          catchError(() => {
            this.availableColumns = []
            // Keep summary usable even if metadata endpoint fails.
            return of([] as Column[])
          }),
        ),
      ),
      switchMap(() => this.loadSummary()),
    )
  }

  loadSummary() {
    if (!this.selectedCycleIds.length) {
      this.fullRowData = []
      this.rowData = []
      this.summary = undefined
      return EMPTY
    }

    if (!this.selectedColumnNames.length && this.availableColumns.length) {
      this.fullRowData = []
      this.rowData = []
      this.summary = undefined
      this.totalExtraData = '0'
      return EMPTY
    }

    const requestColumns
      = !this.availableColumns.length || this.selectedColumnNames.length === this.availableColumns.length ? 'all' : this.selectedColumnNames

    return this._propertyService.columnSummary(this.orgId, this.selectedCycleIds, requestColumns).pipe(
      tap((summary) => {
        this.totalRecords = summary.total_records.toLocaleString()
        this.summary = summary
        this.setAvailableColumns(summary)
        this.setRowData(summary)
        this.setColumnDefs()
      }),
      catchError(() => {
        this.fullRowData = []
        this.rowData = []
        this.summary = undefined
        return EMPTY
      }),
    )
  }

  setGrid() {
    this.setColumnDefs()
  }

  setColumnDefs() {
    const selectedStats = this.availableStatColumns.filter((config) => this.selectedStatKeys.includes(config.key))
    const showCycle = this.selectedCycleIds.length > 1
    this.columnDefs = [
      { field: 'display_name', headerName: 'Field', filter: true, floatingFilter: true, cellRenderer: this.columnRenderer },
      { field: 'cycle_name', headerName: 'Cycle', hide: !showCycle },
      { field: 'is_extra_data', hide: true },
      ...selectedStats.map((config) => ({
        field: config.key,
        headerName: config.label,
        valueFormatter: ({ value }: { value: unknown }) => this.formatStatValue(value),
      })),
    ]

    if (this.gridApi) {
      this.gridApi.setGridOption('columnDefs', this.columnDefs)
      this.gridApi.sizeColumnsToFit()
    }
  }

  columnRenderer = (params: CellRendererParams) => {
    const value = params.value
    const { cycle_name, is_extra_data } = params.data
    if (!is_extra_data && this.selectedCycleIds.length <= 1) return value

    const container = document.createElement('div')

    const valueText = document.createTextNode(value)
    container.append(valueText)

    if (is_extra_data) {
      container.append(document.createTextNode(' '))

      const marker = document.createElement('span')
      marker.className = 'material-icons align-middle ml-1 mb-2 text-secondary text-xs'
      marker.textContent = 'emergency'
      container.append(marker)
    }

    if (this.selectedCycleIds.length > 1) {
      const cycleLabel = document.createElement('div')
      cycleLabel.className = 'text-secondary text-xs'
      cycleLabel.textContent = `Cycle ${cycle_name}`
      container.append(cycleLabel)
    }

    return container
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.applyDisplayedRows()
    this.gridApi.sizeColumnsToFit()
  }

  onSelectionChanged() {
    if (!this.gridApi) {
      return
    }

    const selectedRows = this.gridApi.getSelectedRows() as SummaryGridRow[]
    this.selectedRowIds = new Set(selectedRows.map((row) => row.row_id))
  }

  onGridNativeContextMenu(event: MouseEvent) {
    if (!this.gridApi) {
      return
    }

    const target = event.target as HTMLElement | null

    const headerCell = target?.closest('.ag-header-cell')
    const headerColId = headerCell?.getAttribute('col-id') ?? ''
    if (headerColId && this._isStatKey(headerColId)) {
      event.preventDefault()
      this.contextMenuVisible = true
      this.contextMenuX = event.clientX
      this.contextMenuY = event.clientY
      this.contextMenuMode = 'stat'
      this.contextMenuField = null
      this.contextMenuStatKey = headerColId
      return
    }

    const rowElement = target?.closest('.ag-row')
    const rowIndexAttr = rowElement?.getAttribute('row-index')
    if (!rowIndexAttr) {
      this.closeContextMenu()
      return
    }

    const rowIndex = Number(rowIndexAttr)
    if (Number.isNaN(rowIndex)) {
      this.closeContextMenu()
      return
    }

    const rowNode = this.gridApi.getDisplayedRowAtIndex(rowIndex)
    const row = rowNode?.data as SummaryGridRow | undefined
    if (!row) {
      this.closeContextMenu()
      return
    }

    event.preventDefault()
    this.contextMenuVisible = true
    this.contextMenuX = event.clientX
    this.contextMenuY = event.clientY
    this.contextMenuMode = 'field'
    this.contextMenuField = {
      column_name: row.column_name,
      display_name: row.display_name,
    }
    this.contextMenuStatKey = null
  }

  closeContextMenu() {
    this.contextMenuVisible = false
    this.contextMenuMode = null
    this.contextMenuField = null
    this.contextMenuStatKey = null
  }

  hideContextColumn() {
    if (!this.contextMenuField) {
      return
    }

    this.hideColumnByName(this.contextMenuField.column_name)
    this.closeContextMenu()
  }

  showOnlyContextColumn() {
    if (!this.contextMenuField) {
      return
    }

    this.showOnlyColumnByName(this.contextMenuField.column_name)
    this.closeContextMenu()
  }

  unhideAllContextColumns() {
    this.unhideAllColumns()
    this.closeContextMenu()
  }

  hideContextStatistic() {
    if (!this.contextMenuStatKey) {
      return
    }

    this.selectedStatKeys = this.selectedStatKeys.filter((key) => key !== this.contextMenuStatKey)
    this.setColumnDefs()
    this.persistSummarySettings().subscribe()
    this.closeContextMenu()
  }

  hideColumnByName(columnName: string) {
    const nextColumns = this.selectedColumnNames.filter((selectedName) => selectedName !== columnName)
    if (!nextColumns.length) {
      return
    }

    this.selectedColumnNames = nextColumns
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  showOnlyColumnByName(columnName: string) {
    this.selectedColumnNames = [columnName]
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  setAvailableColumns(summary: PropertyColumnSummaryResponse) {
    if (!this.availableColumns.length) {
      const byName = new Map<string, Pick<PropertyColumnSummary, 'column_name' | 'display_name' | 'is_extra_data'>>()
      for (const cycle of summary.cycles) {
        for (const column of cycle.columns) {
          if (!byName.has(column.column_name)) {
            byName.set(column.column_name, {
              column_name: column.column_name,
              display_name: column.display_name,
              is_extra_data: column.is_extra_data,
            })
          }
        }
      }
      this.availableColumns = [...byName.values()]
    }

    const availableColumnNames = new Set(this.availableColumns.map((column) => column.column_name))
    this.hasSavedColumnSelection = Array.isArray(this.currentUser.settings.summaryColumnNames)
    const savedColumnNames = this._getSavedColumnNames(availableColumnNames)

    if (!this.selectedColumnNames.length && this.hasSavedColumnSelection) {
      this.selectedColumnNames = savedColumnNames
    }

    if (!this.selectedColumnNames.length && !this.hasSavedColumnSelection) {
      this.selectedColumnNames = this.availableColumns.map((column) => column.column_name)
    }
  }

  setAvailableColumnsFromColumns(columns: Column[]) {
    const propertyColumns = columns
      .filter((column) => column.table_name === 'PropertyState' && !column.derived_column)
      .map((column) => ({
        column_name: column.column_name,
        display_name: column.display_name,
        is_extra_data: column.is_extra_data,
      }))

    if (!propertyColumns.length) {
      return
    }

    this.availableColumns = propertyColumns

    const availableColumnNames = new Set(this.availableColumns.map((column) => column.column_name))
    this.hasSavedColumnSelection = Array.isArray(this.currentUser.settings.summaryColumnNames)
    const savedColumnNames = this._getSavedColumnNames(availableColumnNames)

    if (this.hasSavedColumnSelection) {
      this.selectedColumnNames = savedColumnNames
    } else {
      this.selectedColumnNames = this.availableColumns.map((column) => column.column_name)
    }
  }

  setRowData(summary: PropertyColumnSummaryResponse) {
    this.fullRowData = summary.cycles.flatMap((cycle) =>
      cycle.columns.map((column) => ({
        avg: column.stats.avg,
        blank_count: column.stats.blank_count,
        column_name: column.column_name,
        cycle_id: cycle.cycle_id,
        cycle_name: this.getCycleName(cycle.cycle_id),
        display_name: column.display_name,
        distinct_count: column.stats.distinct_count,
        is_extra_data: column.is_extra_data,
        max: column.stats.max,
        median: column.stats.median,
        min: column.stats.min,
        mode: column.stats.mode,
        non_null_count: column.stats.non_null_count,
        null_count: column.stats.null_count,
        p05: column.stats.p05,
        p25: column.stats.p25,
        p75: column.stats.p75,
        p95: column.stats.p95,
        row_id: `${column.column_name}::${cycle.cycle_id}`,
        stddev: column.stats.stddev,
        sum: column.stats.sum,
        unique_count: column.stats.unique_count,
        uniqueness_ratio: column.stats.uniqueness_ratio,
      })),
    )

    const validRowIds = new Set(this.fullRowData.map((row) => row.row_id))
    this.selectedRowIds = new Set([...this.selectedRowIds].filter((id) => validRowIds.has(id)))
    this.applyDisplayedRows()
    this.totalExtraData = this.availableColumns.filter((column) => column.is_extra_data).length.toLocaleString()
  }

  showSelectedRows() {
    const selectedColumnNames = this.getSelectedColumnNamesFromRows()
    if (selectedColumnNames.length) {
      this.selectedColumnNames = selectedColumnNames
    }

    this.selectedRowsOnly = true
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  showAllRows() {
    this.selectedRowsOnly = false
    this.applyDisplayedRows()
  }

  clearSelectedRows() {
    this.selectedRowIds.clear()
    if (this.gridApi) {
      this.gridApi.deselectAll()
    }
    this.applyDisplayedRows()
  }

  hideSelectedColumns() {
    const columnsToHide = new Set(this.getSelectedColumnNamesFromRows())
    if (!columnsToHide.size) {
      return
    }

    this.selectedColumnNames = this.selectedColumnNames.filter((columnName) => !columnsToHide.has(columnName))
    this.selectedRowsOnly = false
    this.selectedRowIds.clear()
    if (this.gridApi) {
      this.gridApi.deselectAll()
    }

    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  unhideAllColumns() {
    this.selectedColumnNames = this.availableColumns.map((column) => column.column_name)
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  applyDisplayedRows() {
    this.rowData = this.selectedRowsOnly ? this.fullRowData.filter((row) => this.selectedRowIds.has(row.row_id)) : this.fullRowData

    if (this.gridApi) {
      this.gridApi.setGridOption('rowData', this.rowData)
      this.gridApi.forEachNode((node) => {
        const rowId = (node.data as SummaryGridRow | undefined)?.row_id
        node.setSelected(rowId ? this.selectedRowIds.has(rowId) : false)
      })
      this.gridApi.sizeColumnsToFit()
    }
  }

  getCycleName(cycleId: number): string {
    return this.cycles.find((cycle) => cycle.cycle_id === cycleId)?.name ?? `Cycle ${cycleId}`
  }

  getCyclePickerLabel(maxNames = 2): string {
    const source = this.cyclePickerOpen ? this.pendingCycleIds : this.selectedCycleIds
    if (!source.length) {
      return 'No cycles selected'
    }

    const names = source.map((cycleId) => this.getCycleName(cycleId))
    const visible = names.slice(0, maxNames)
    const hiddenCount = names.length - visible.length

    return hiddenCount > 0 ? `${visible.join(', ')} +${hiddenCount}` : visible.join(', ')
  }

  getSelectedRowCount(): number {
    return this.selectedRowIds.size
  }

  getDisplayedRowCount(): number {
    return this.rowData.length
  }

  getTotalRowCount(): number {
    return this.fullRowData.length
  }

  getRowDisplayLabel(): string {
    if (this.selectedRowsOnly) {
      return `${this.getDisplayedRowCount()} selected rows shown`
    }
    return `${this.getTotalRowCount()} rows`
  }

  exportSummaryCsv() {
    if (!this.gridApi) {
      return
    }

    const dateStamp = new Date().toISOString().slice(0, 10)
    this.gridApi.exportDataAsCsv({
      fileName: `summary-${this.type}-${dateStamp}.csv`,
    })
  }

  getSelectedColumnNamesFromRows(): string[] {
    if (!this.selectedRowIds.size) {
      return []
    }

    return [...new Set(this.fullRowData.filter((row) => this.selectedRowIds.has(row.row_id)).map((row) => row.column_name))]
  }

  selectCycles(cycleIds: number[]) {
    this.selectedCycleIds = cycleIds ?? []
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  toggleCyclePicker() {
    if (this.cyclePickerOpen) {
      this.closeCyclePicker()
      return
    }

    this.pendingCycleIds = [...this.selectedCycleIds]
    this.cyclePickerOpen = true
  }

  closeCyclePicker() {
    const changed = !this._sameNumberSelection(this.selectedCycleIds, this.pendingCycleIds)
    this.cyclePickerOpen = false
    if (changed) {
      this.selectCycles(this.pendingCycleIds)
    }
  }

  cancelCyclePicker() {
    this.pendingCycleIds = [...this.selectedCycleIds]
    this.cyclePickerOpen = false
  }

  selectAllCycles() {
    const allCycleIds = this.cycles.map((cycle) => cycle.cycle_id)
    if (this.cyclePickerOpen) {
      this.pendingCycleIds = allCycleIds
      return
    }

    this.selectCycles(allCycleIds)
  }

  clearAllCycles() {
    if (this.cyclePickerOpen) {
      this.pendingCycleIds = []
      return
    }

    this.selectCycles([])
  }

  isCycleSelected(cycleId: number): boolean {
    const source = this.cyclePickerOpen ? this.pendingCycleIds : this.selectedCycleIds
    return source.includes(cycleId)
  }

  toggleCycleSelection(cycleId: number, checked: boolean) {
    const source = this.cyclePickerOpen ? this.pendingCycleIds : this.selectedCycleIds
    const next = checked ? [...new Set([...source, cycleId])] : source.filter((id) => id !== cycleId)

    if (this.cyclePickerOpen) {
      this.pendingCycleIds = next
      return
    }

    this.selectCycles(next)
  }

  selectAllColumns() {
    const allColumns = this.availableColumns.map((column) => column.column_name)
    if (this.columnPickerOpen) {
      this.pendingColumnNames = allColumns
      return
    }

    this.selectedColumnNames = allColumns
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  toggleColumnPicker() {
    if (this.columnPickerOpen) {
      this.closeColumnPicker()
      return
    }

    this.pendingColumnNames = [...this.selectedColumnNames]
    this.columnPickerOpen = true
    this.columnPickerShowSelectedOnly = false
    this.setColumnSearchTerm('')
  }

  closeColumnPicker() {
    const changed = !this._sameSelection(this.selectedColumnNames, this.pendingColumnNames)
    this.columnPickerOpen = false
    if (changed) {
      this.selectedColumnNames = [...this.pendingColumnNames]
      this.persistSummarySettings()
        .pipe(switchMap(() => this.loadSummary()))
        .subscribe()
    }
  }

  cancelColumnPicker() {
    this.pendingColumnNames = [...this.selectedColumnNames]
    this.columnPickerOpen = false
  }

  selectFilteredColumns() {
    const filteredColumnNames = this.filteredAvailableColumns().map((column) => column.column_name)
    if (!filteredColumnNames.length) {
      return
    }

    const base = this.columnPickerOpen ? this.pendingColumnNames : this.selectedColumnNames
    const next = new Set(base)
    for (const name of filteredColumnNames) {
      next.add(name)
    }

    if (this.columnPickerOpen) {
      this.pendingColumnNames = [...next]
      return
    }

    this.selectedColumnNames = [...next]
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  clearAllColumns() {
    if (this.columnPickerOpen) {
      this.pendingColumnNames = []
      return
    }

    this.selectedColumnNames = []
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  isColumnSelected(columnName: string): boolean {
    const source = this.columnPickerOpen ? this.pendingColumnNames : this.selectedColumnNames
    return source.includes(columnName)
  }

  toggleColumnSelection(columnName: string, checked: boolean) {
    const source = this.columnPickerOpen ? this.pendingColumnNames : this.selectedColumnNames
    const next = checked ? [...new Set([...source, columnName])] : source.filter((name) => name !== columnName)

    if (this.columnPickerOpen) {
      this.pendingColumnNames = next
      return
    }

    this.selectColumns(next)
  }

  selectColumns(columnNames: string[]) {
    this.selectedColumnNames = columnNames ?? []
    this.persistSummarySettings()
      .pipe(switchMap(() => this.loadSummary()))
      .subscribe()
  }

  setColumnSearchTerm(value: string) {
    this.columnSearchTerm = value ?? ''
  }

  setColumnPickerShowSelectedOnly(showSelectedOnly: boolean) {
    this.columnPickerShowSelectedOnly = showSelectedOnly
  }

  filteredAvailableColumns() {
    const selectedSource = this.columnPickerOpen ? this.pendingColumnNames : this.selectedColumnNames
    const selectedSet = new Set(selectedSource)
    const baseColumns = this.columnPickerShowSelectedOnly
      ? this.availableColumns.filter((column) => selectedSet.has(column.column_name))
      : this.availableColumns

    const search = this.columnSearchTerm.trim().toLowerCase()
    if (!search) {
      return baseColumns
    }

    return baseColumns.filter(
      (column) =>
        (column.display_name || column.column_name).toLowerCase().includes(search) || column.column_name.toLowerCase().includes(search),
    )
  }

  selectAllStats() {
    const allStatKeys = this.availableStatColumns.map((config) => config.key)
    if (this.statPickerOpen) {
      this.pendingStatKeys = allStatKeys
      return
    }

    this.selectedStatKeys = allStatKeys
    this.setColumnDefs()
    this.persistSummarySettings().subscribe()
  }

  clearAllStats() {
    if (this.statPickerOpen) {
      this.pendingStatKeys = []
      return
    }

    this.selectedStatKeys = []
    this.setColumnDefs()
    this.persistSummarySettings().subscribe()
  }

  toggleStatPicker() {
    if (this.statPickerOpen) {
      this.closeStatPicker()
      return
    }

    this.pendingStatKeys = [...this.selectedStatKeys]
    this.statPickerOpen = true
  }

  closeStatPicker() {
    const changed = !this._sameStatSelection(this.selectedStatKeys, this.pendingStatKeys)
    this.statPickerOpen = false
    if (changed) {
      this.selectStatColumns(this.pendingStatKeys)
    }
  }

  cancelStatPicker() {
    this.pendingStatKeys = [...this.selectedStatKeys]
    this.statPickerOpen = false
  }

  isStatSelected(statKey: StatKey): boolean {
    const source = this.statPickerOpen ? this.pendingStatKeys : this.selectedStatKeys
    return source.includes(statKey)
  }

  toggleStatSelection(statKey: StatKey, checked: boolean) {
    const source = this.statPickerOpen ? this.pendingStatKeys : this.selectedStatKeys
    const next = checked ? [...new Set([...source, statKey])] : source.filter((key) => key !== statKey)

    if (this.statPickerOpen) {
      this.pendingStatKeys = next
      return
    }

    this.selectStatColumns(next)
  }

  selectStatColumns(statKeys: StatKey[]) {
    this.selectedStatKeys = statKeys ?? []
    this.setColumnDefs()
    this.persistSummarySettings().subscribe()
  }

  persistSummarySettings() {
    this.currentUser.settings.summaryCycleIds = this.selectedCycleIds
    this.currentUser.settings.summaryColumnNames = this.selectedColumnNames
    this.currentUser.settings.summaryStatColumns = this.selectedStatKeys
    this.currentUser.settings.cycleId = this.selectedCycleIds[0] ?? this.currentUser.settings.cycleId
    return this.updateOrgUserSettings()
  }

  formatStatValue(value: unknown): string {
    if (value == null) {
      return ''
    }

    if (typeof value === 'number') {
      return this._numberFormatter.format(this.smartRoundNumber(value))
    }

    if (typeof value === 'string' || typeof value === 'boolean') {
      return String(value)
    }

    return ''
  }

  smartRoundNumber(value: number): number {
    if (!Number.isFinite(value) || value === 0) {
      return value
    }

    const absValue = Math.abs(value)

    // Keep large magnitudes concise while preserving useful precision for small values.
    if (absValue >= 10000) {
      return Math.round(value)
    }

    if (absValue >= 1000) {
      return Math.round(value * 10) / 10
    }

    if (absValue >= 100) {
      return Math.round(value * 100) / 100
    }

    if (absValue >= 1) {
      return Math.round(value * 1000) / 1000
    }

    return Number(value.toPrecision(3))
  }

  updateOrgUserSettings() {
    return this._organizationService.updateOrganizationUser(this.currentUser.org_user_id, this.orgId, this.currentUser.settings)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  private _getSavedNumberArray(settingName: string): number[] {
    const value = this.currentUser.settings[settingName]
    if (!Array.isArray(value)) {
      return []
    }

    return value.filter((item): item is number => typeof item === 'number')
  }

  private _getSavedColumnNames(availableColumnNames: Set<string>): string[] {
    const value = this.currentUser.settings.summaryColumnNames
    if (!Array.isArray(value)) {
      return []
    }

    return value.filter((columnName): columnName is string => typeof columnName === 'string' && availableColumnNames.has(columnName))
  }

  private _getSavedStatKeys(availableStatKeys: Set<StatKey>): StatKey[] {
    const value = this.currentUser.settings.summaryStatColumns
    if (!Array.isArray(value)) {
      return []
    }

    return value.filter((key): key is StatKey => typeof key === 'string' && availableStatKeys.has(key as StatKey))
  }

  private _isStatKey(value: string): value is StatKey {
    return this.availableStatColumns.some((config) => config.key === value)
  }

  private _sameSelection(left: string[], right: string[]): boolean {
    if (left.length !== right.length) {
      return false
    }

    const rightSet = new Set(right)
    return left.every((item) => rightSet.has(item))
  }

  private _sameNumberSelection(left: number[], right: number[]): boolean {
    if (left.length !== right.length) {
      return false
    }

    const rightSet = new Set(right)
    return left.every((item) => rightSet.has(item))
  }

  private _sameStatSelection(left: StatKey[], right: StatKey[]): boolean {
    if (left.length !== right.length) {
      return false
    }

    const rightSet = new Set(right)
    return left.every((item) => rightSet.has(item))
  }

  private _matchesFilterExpression(params: TextMatcherParams): boolean {
    const rawFilterText = (params.filterText ?? '').trim()
    const value: unknown = params.value as unknown
    const valueText
      = typeof value === 'string'
        ? value
        : typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint'
          ? String(value)
          : ''
    const normalizedValue = valueText.toLowerCase()

    if (!rawFilterText) {
      return true
    }

    const parsed = this._parseFilterExpression(rawFilterText)
    const normalizedFilter = parsed.value.toLowerCase()

    if (!parsed.value) {
      return true
    }

    const valueNumber = typeof value === 'number' ? value : typeof value === 'string' && value.trim() !== '' ? Number(value) : NaN
    const filterNumber = Number(parsed.value)
    const bothNumeric = Number.isFinite(valueNumber) && Number.isFinite(filterNumber)

    if (parsed.operator === '>') {
      return bothNumeric ? valueNumber > filterNumber : normalizedValue > normalizedFilter
    }
    if (parsed.operator === '>=') {
      return bothNumeric ? valueNumber >= filterNumber : normalizedValue >= normalizedFilter
    }
    if (parsed.operator === '<') {
      return bothNumeric ? valueNumber < filterNumber : normalizedValue < normalizedFilter
    }
    if (parsed.operator === '<=') {
      return bothNumeric ? valueNumber <= filterNumber : normalizedValue <= normalizedFilter
    }
    if (parsed.operator === '!=') {
      return bothNumeric ? valueNumber !== filterNumber : normalizedValue !== normalizedFilter
    }
    if (parsed.operator === '=') {
      return bothNumeric ? valueNumber === filterNumber : normalizedValue === normalizedFilter
    }

    // Default behavior when no operator is provided.
    return normalizedValue.includes(normalizedFilter)
  }

  private _parseFilterExpression(input: string): { operator: '>' | '>=' | '<' | '<=' | '!=' | '=' | null; value: string } {
    const match = /^\s*(>=|<=|!=|>|<|=)\s*(.*)$/.exec(input)
    if (!match) {
      return { operator: null, value: input.trim() }
    }

    const [, operator, value] = match
    return {
      operator: operator as '>' | '>=' | '<' | '<=' | '!=' | '=' | null,
      value: value.trim(),
    }
  }
}
