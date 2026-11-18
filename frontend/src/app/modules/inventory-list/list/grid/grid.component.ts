import { CommonModule } from '@angular/common'
import type { OnChanges, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { Router } from '@angular/router'
import { TranslocoService } from '@jsverse/transloco'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, CellKeyDownEvent, ColDef, GridApi, GridOptions, GridReadyEvent } from 'ag-grid-community'
import { map } from 'rxjs'
import type { CurrentUser, Label, OrganizationUserSettings } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { ConfigService } from '@seed/services'
import type { FiltersSorts, InventoryType, Pagination, State } from '../../../inventory'
import { CellHeaderMenuComponent } from './cell-header-menu.component'
import { InventoryGridControlsComponent } from './grid-controls.component'
import { IconHeaderComponent } from './icon-header.component'
import { InventoryLabelHeaderComponent } from './label-header.component'

const SHORTCUT_COLUMN_WIDTH = 34
const SHORTCUT_COLUMN_PADDING = { paddingLeft: '0', paddingRight: '0' }

type ShortcutAction = 'detail' | 'notes' | 'meters'

// Shortcut columns whose icon navigates somewhere (by click, or Enter/Space when the cell has keyboard focus)
const SHORTCUT_ACTIONS: Record<string, ShortcutAction> = {
  property_view_id: 'detail',
  taxlot_view_id: 'detail',
  notes_count: 'notes',
  meters_exist_indicator: 'meters',
}

export const LABEL_COLOR_MAP: Record<string, string> = {
  red: '#b91c1c',
  orange: '#fb923c',
  gray: '#57534e',
  green: '#15803d',
  blue: '#1d4ed8',
  'light blue': '#0891b2',
  white: '#e5e7eb',
}

@Component({
  selector: 'seed-inventory-grid',
  templateUrl: './grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, InventoryGridControlsComponent],
  host: { class: 'flex flex-col flex-auto min-h-0' },
})
export class InventoryGridComponent implements OnChanges {
  @Input() accessLevelNames: string[] = []
  @Input() columnDefs!: ColDef[]
  @Input() currentUser: CurrentUser
  @Input() inventoryType: string
  @Input() labelMap: Record<number, Label>
  @Input() orgId: number
  @Input() orgUserId: number
  @Input() pagination!: Pagination
  @Input() rowData!: Record<string, unknown>[]
  @Input() selectedViewIds: number[]
  @Input() type: InventoryType
  @Input() userSettings: OrganizationUserSettings
  @Output() pageChange = new EventEmitter<number>()
  @Output() filterSortChange = new EventEmitter<FiltersSorts>()
  @Output() gridReady = new EventEmitter<GridApi>()
  @Output() selectionChanged = new EventEmitter<null>()
  @Output() selectAllMatching = new EventEmitter<void>()
  @Output() gridReset = new EventEmitter<null>()
  private _configService = inject(ConfigService)
  private _organizationService = inject(OrganizationService)
  private _router = inject(Router)
  private _transloco = inject(TranslocoService)

  agPageSize = 100
  gridApi!: GridApi
  darkMode: boolean
  // rowHeight trims ~3px off the top and bottom of the default 42px row so more records fit on screen
  gridTheme$ = this._configService.gridTheme$.pipe(map((theme) => theme.withParams({ cellHorizontalPadding: 8, rowHeight: 36 })))
  showAccessLevelInstances = true
  labelsExpanded = false

  readonly gridContext = {
    labelsExpanded: false,
    toggleLabels: () => {
      this.toggleLabels()
    },
  }

  theme: string

  defaultColDef = {
    sortable: true,
    filter: true,
    floatingFilter: true,
    resizable: true,
    filterParams: {
      suppressAndOrCondition: true,
    },
  }
  gridOptions: GridOptions = {
    rowSelection: {
      mode: 'multiRow',
      checkboxes: true,
      headerCheckbox: true,
    },
    selectionColumnDef: { pinned: 'left', lockPinned: true, lockPosition: 'left' },
    rowClassRules: {
      'even-row': (params) => params.node.rowIndex % 2 === 0,
    },
    onSelectionChanged: () => {
      this.onSelectionChanged()
    },
    onRowDataUpdated: () => {
      this._syncSelectedRows()
      this._updatingRowData = false
    },
  }

  // Raw API column defs — kept separate so getColumnDefs() doesn't clobber them by overwriting this.columnDefs
  private _apiColumnDefs: ColDef[] = []
  private _syncingSelection = false
  private _updatingRowData = false

  ngOnChanges(changes: SimpleChanges) {
    if (changes.rowData) {
      this._updatingRowData = true
    }
    if (changes.columnDefs) {
      this._apiColumnDefs = this.columnDefs ?? []
    }
    if (changes.rowData || changes.columnDefs) {
      this.getColumnDefs()
    }
    if (changes.selectedViewIds && this.gridApi) {
      this._syncSelectedRows()
    }
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi = params.api
    this.gridReady.emit(this.gridApi)
    this._syncSelectedRows()
    this._updatingRowData = false
    this.gridApi.autoSizeAllColumns()
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
    this.gridApi.addEventListener('cellKeyDown', this.onCellKeyDown.bind(this) as (event: CellKeyDownEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (!SHORTCUT_ACTIONS[event.colDef.field]) return

    const target = event.event.target as HTMLElement
    const action = target.getAttribute('data-action') as ShortcutAction | null
    if (!action) return
    this.navigateToShortcut(action, event.data as Record<string, unknown>)
  }

  // Keyboard equivalent of clicking a shortcut icon
  onCellKeyDown(event: CellKeyDownEvent) {
    const { key } = event.event as KeyboardEvent
    if (key !== 'Enter' && key !== ' ') return

    const action = SHORTCUT_ACTIONS[event.colDef.field]
    if (!action || !event.value) return
    event.event.preventDefault()
    this.navigateToShortcut(action, event.data as Record<string, unknown>)
  }

  navigateToShortcut(action: ShortcutAction, data: Record<string, unknown>) {
    const viewId = data.property_view_id || data.taxlot_view_id
    const urlMap: Record<ShortcutAction, unknown[]> = {
      detail: [`/${this.inventoryType}`, viewId],
      notes: [`/${this.inventoryType}`, viewId, 'notes'],
      meters: [`/${this.inventoryType}`, viewId, 'meters'],
    }

    void this._router.navigate(urlMap[action])
  }

  onSelectionChanged() {
    if (this._syncingSelection || this._updatingRowData) return
    this.selectionChanged.emit()
  }

  getColumnDefs() {
    const stateColumns = this.addHeaderMenu()
    this.columnDefs = [...this.getShortcutColumns(), ...this.getAccessLevelColumns(), ...stateColumns]
  }

  getAccessLevelColumns(): ColDef[] {
    if (!this.accessLevelNames?.length) return []
    // Skip root level (index 0) — it's always the same for all instances
    const names = this.accessLevelNames.slice(1)
    return names.map((name) => ({
      field: name,
      headerName: name,
      // Pinned left so user-pinned columns appear to the right of ALI columns
      pinned: 'left' as const,
      hide: !this.showAccessLevelInstances,
      filter: true,
      sortable: false,
      resizable: true,
      minWidth: 100,
      headerClass: 'access-level-header',
      cellClass: 'access-level-cell',
    }))
  }

  toggleAccessLevelInstances() {
    this.showAccessLevelInstances = !this.showAccessLevelInstances
    if (this.gridApi) {
      const names = (this.accessLevelNames ?? []).slice(1)
      this.gridApi.setColumnsVisible(names, this.showAccessLevelInstances)
    }
  }

  toggleLabels(): void {
    this.labelsExpanded = !this.labelsExpanded
    this.gridContext.labelsExpanded = this.labelsExpanded
    this.gridApi?.setColumnWidths([{ key: 'labels', newWidth: this.labelsExpanded ? 320 : SHORTCUT_COLUMN_WIDTH }])
    this.gridApi?.refreshHeader()
    this.gridApi?.refreshCells({ force: true, columns: ['labels'] })
  }

  getShortcutColumns(): ColDef[] {
    const shortcutColumns = [
      this.buildInfoCell(),
      this.buildShortcutColumn('merged_indicator', 'Merged', SHORTCUT_COLUMN_WIDTH, 'merge'),
      this.buildShortcutColumn('meters_exist_indicator', 'Meters', SHORTCUT_COLUMN_WIDTH, 'bolt', 'meters'),
      this.buildShortcutColumn('notes_count', 'Notes', SHORTCUT_COLUMN_WIDTH, 'mode_comment', 'notes'),
      this.buildShortcutColumn('groups_indicator', 'Groups', SHORTCUT_COLUMN_WIDTH, 'workspaces'),
      this.buildLabelsCell(),
    ]
    // Pin shortcuts so user-pinned columns land after them in the pinned area
    return shortcutColumns.map((c) => ({ ...c, pinned: 'left' as const }))
  }

  addHeaderMenu() {
    const stateColumns = this._apiColumnDefs.map((c) => ({
      ...c,
      headerComponent: CellHeaderMenuComponent,
      headerComponentParams: {
        currentUser: this.currentUser,
        type: this.type,
      },
    }))
    return stateColumns
  }

  buildShortcutColumn(field: string, headerName: string, maxWidth: number, icon: string, action: string = null): ColDef {
    return {
      field,
      headerName,
      headerTooltip: headerName,
      headerComponent: IconHeaderComponent,
      headerComponentParams: { icon, tooltip: headerName },
      width: maxWidth,
      maxWidth,
      cellStyle: SHORTCUT_COLUMN_PADDING,
      headerStyle: SHORTCUT_COLUMN_PADDING,
      filter: false,
      sortable: false,
      suppressMovable: true,
      cellClass: 'overflow-hidden',
      cellRenderer: ({ value }) => this.actionRenderer({ value, icon, action, label: headerName }),
    }
  }

  buildInfoCell() {
    const field = this.type === 'taxlots' ? 'taxlot_view_id' : 'property_view_id'
    return {
      field,
      headerName: 'Info',
      headerTooltip: 'Info',
      headerComponent: IconHeaderComponent,
      headerComponentParams: { icon: 'info', tooltip: 'Info' },
      filter: false,
      sortable: false,
      suppressMovable: true,
      width: SHORTCUT_COLUMN_WIDTH,
      maxWidth: SHORTCUT_COLUMN_WIDTH,
      cellStyle: SHORTCUT_COLUMN_PADDING,
      headerStyle: SHORTCUT_COLUMN_PADDING,
      cellRenderer: ({ value }) => this.actionRenderer({ value, icon: 'info', action: 'detail', label: 'Info' }),
    }
  }

  actionRenderer = ({ value, icon, action, label }: { value: unknown; icon: string; action: string | null; label: string }) => {
    if (!value) return ''

    // Clickable icons are announced as buttons; indicator-only icons as images. Both carry a text alternative.
    const cursorClass = action ? 'cursor-pointer' : ''
    const role = action ? 'button' : 'img'
    const ariaLabel = this._transloco.translate(label)
    // Same size and centering as IconHeaderComponent so row icons line up with their headers
    return `
      <div class="flex h-full items-center justify-center">
        <span class="material-icons-outlined text-base ${cursorClass}" role="${role}" aria-label="${ariaLabel}" data-action="${action}">${icon}</span>
      </div>
    `
  }

  buildLabelsCell(): ColDef {
    return {
      colId: 'labels',
      field: 'labels',
      headerName: 'Labels',
      width: SHORTCUT_COLUMN_WIDTH,
      filter: false,
      sortable: false,
      suppressMovable: true,
      cellStyle: SHORTCUT_COLUMN_PADDING,
      headerStyle: SHORTCUT_COLUMN_PADDING,
      headerComponent: InventoryLabelHeaderComponent,
      autoHeight: true,
      valueFormatter: ({ value }: { value: number[] }) => {
        return this.getShownLabels(value)
          .map((label) => label.name)
          .join(', ')
      },
      cellRenderer: ({ value }: { value: number[] }) => {
        const labels = this.getShownLabels(value)
        if (!labels.length) {
          const container = document.createElement('div')
          container.style.minHeight = '36px'
          return container
        }
        if (this.labelsExpanded) {
          const container = document.createElement('div')
          container.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;align-items:center;align-content:center;min-height:36px;'
          for (const label of labels) {
            const colorClass = label.color === 'light blue' ? 'blue light' : label.color
            const span = document.createElement('span')
            span.className = `label compact ${colorClass} whitespace-nowrap`
            span.textContent = label.name
            container.appendChild(span)
          }
          return container
        }
        const outer = document.createElement('div')
        outer.style.cssText = 'min-height:36px;display:flex;align-items:center;'
        const inner = document.createElement('div')
        inner.style.cssText = 'display:flex;width:26px;height:14px;border-radius:3px;overflow:hidden;'
        for (const label of labels.slice(0, 4)) {
          const bg = LABEL_COLOR_MAP[label.color] ?? LABEL_COLOR_MAP.gray
          const span = document.createElement('span')
          span.style.cssText = `flex:1;min-width:0;background-color:${bg};`
          span.title = label.name
          inner.appendChild(span)
        }
        outer.appendChild(inner)
        return outer
      },
    }
  }

  /*
   * ascending sorts formatted as 'column_id'
   * descending sorts formatted as '-column_id'
   */
  getSorts() {
    const sorts = this.gridApi
      .getColumnState()
      .filter((col) => col.sort)
      .map((col) => `${col.sort === 'desc' ? '-' : ''}${col.colId}`)
    return sorts
  }

  onFilterSortChange() {
    const filters = this.gridApi.getFilterModel()
    const sorts = this.getSorts()
    this.filterSortChange.emit({ sorts, filters })
  }

  onPageChange(page: number) {
    this.pageChange.emit(page)
  }

  getShownLabels(labelIds: number[]): Label[] {
    if (!labelIds?.length) return []
    return labelIds.map((id) => this.labelMap[id]).filter((label) => label?.show_in_list)
  }

  private _syncSelectedRows(): void {
    if (!this.gridApi) return

    const selectedViewIds = new Set(this.selectedViewIds ?? [])
    const viewIdField = this.type === 'taxlots' ? 'taxlot_view_id' : 'property_view_id'

    this._syncingSelection = true
    try {
      this.gridApi.forEachNode((node) => {
        const state = node.data as State | undefined
        const viewId = state?.[viewIdField]
        node.setSelected(selectedViewIds.has(viewId), false)
      })
    } finally {
      this._syncingSelection = false
    }
  }
}
