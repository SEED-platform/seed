import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import type { MatSelectChange } from '@angular/material/select'
import { TranslocoService } from '@jsverse/transloco'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, GridApi, GridOptions, GridReadyEvent, ICellRendererParams, RowSelectedEvent } from 'ag-grid-community'
import { combineLatest, filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Column, CurrentUser } from '@seed/api'
import { ColumnService, InventoryService, OrganizationService, UserService } from '@seed/api'
import { DeleteModalComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { ModalComponent } from 'app/modules/column-list-profile/modal/modal.component'
import type { InventoryDisplayType, InventoryType, Profile, ProfileColumn, ProfileModalMode } from 'app/modules/inventory/inventory.types'

type CellRendererParams = { value: string; data: ProfileColumn & { is_extra_data: boolean } }
type ProfileColumnSettings = Pick<ProfileColumn, 'id'> & Partial<Pick<ProfileColumn, 'order' | 'pinned'>>
@Component({
  selector: 'seed-column-profiles',
  templateUrl: './column-profiles.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports],
})
export class ColumnProfilesComponent implements OnDestroy, OnInit {
  @Input() profileType: 'list' | 'detail'
  @Input() type: InventoryType
  private _configService = inject(ConfigService)
  private _columnService = inject(ColumnService)
  private _dialog = inject(MatDialog)
  private _inventoryService = inject(InventoryService)
  private _organizationService = inject(OrganizationService)
  private _translocoService = inject(TranslocoService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  columnDefs: ColDef[] = []
  columns: Column[]
  currentProfile: Profile
  currentUser: CurrentUser
  displayType: InventoryDisplayType
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  orgId: number
  profiles: Profile[]
  profileLocation: 'List View Profile' | 'Detail View Profile'
  updateCLP$ = new Subject<unknown>()
  updateOrgUserSettings$ = new Subject<void>()
  rowData: ProfileColumn[] = []
  private _rowSelectedTimer: ReturnType<typeof setTimeout>
  private _selectionTimer: ReturnType<typeof setTimeout>

  gridOptions: GridOptions = {
    rowDragManaged: true,
    selectionColumnDef: { width: 44, maxWidth: 44, resizable: false },
    getRowId: (params) => String((params.data as ProfileColumn).id),
    rowSelection: {
      mode: 'multiRow',
      checkboxes: true,
      headerCheckbox: true,
    },
    onRowSelected: (event) => {
      this.onRowSelected(event)
    },
    onRowDragEnd: () => {
      this.onRowDragEnd()
    },
  }

  defaultColDef = {
    sortable: false,
    filter: true,
    resizable: true,
    suppressMovable: true,
    floatingFilter: true,
  }

  ngOnInit(): void {
    this.profileLocation = this.profileType === 'list' ? 'List View Profile' : 'Detail View Profile'
    this.displayType = this.type === 'taxlots' ? 'Tax Lot' : 'Property'
    this.initStreams()
    this.initPage()
  }

  initPage() {
    this.getDependencies()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.setGrid()
        }),
      )
      .subscribe()
  }

  initStreams() {
    this.updateCLP$
      .pipe(
        filter(Boolean),
        takeUntil(this._unsubscribeAll$),
        switchMap((data) => this._inventoryService.updateColumnListProfile(this.orgId, this.currentProfile.id, data)),
        tap((profile) => {
          this.profiles = this.profiles.map((existing) => (existing.id === profile.id ? profile : existing))
          if (this.currentProfile?.id === profile.id) {
            this.currentProfile = profile
            this.setGrid()
          }
        }),
      )
      .subscribe()

    this.updateOrgUserSettings$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(() => this.updateOrgUserSettings()),
      )
      .subscribe()
  }

  getDependencies() {
    const columns$ = this.type === 'taxlots' ? this._columnService.taxLotColumns$ : this._columnService.propertyColumns$

    return combineLatest([this._userService.currentOrganizationId$, this._userService.currentUser$, columns$]).pipe(
      tap(([orgId, currentUser, columns]) => {
        this.orgId = orgId
        this.currentUser = currentUser
        this.columns = columns
      }),
      switchMap(() => this._inventoryService.getColumnListProfiles(this.profileLocation, this.type)),
      switchMap((profiles) => {
        this.profiles = profiles.filter((p) => p.inventory_type === this.displayType).sort((a, b) => naturalSort(a.name, b.name))
        return this.setProfile()
      }),
    )
  }

  setProfile() {
    if (!this.currentUser.settings.profile) return

    const userProfileId = this.currentUser.settings.profile[this.profileType][this.type]
    this.currentProfile = this.profiles.find((p) => p.id === userProfileId) ?? this.profiles[0]
    this.currentUser.settings.profile[this.profileType][this.type] = this.currentProfile?.id
    return this.updateOrgUserSettings()
  }

  updateOrgUserSettings() {
    return this._organizationService.updateOrganizationUser(this.currentUser.org_user_id, this.orgId, this.currentUser.settings)
  }

  setGrid() {
    this.setColumnDefs()
    // use current profile if it exists, otherwise use all canonical columns
    const selectedCols = this.currentProfile?.columns ?? this.columns.filter((c) => !c.is_extra_data && !c.derived_column)
    const selectedColIds = new Set(selectedCols.map((c: { id: number }) => c.id))
    this.setRowData(selectedColIds, selectedCols)
  }

  setColumnDefs() {
    this.columnDefs = [
      {
        field: 'pinned',
        headerName: '',
        hide: this.profileType !== 'list',
        width: 44,
        maxWidth: 44,
        sortable: false,
        filter: false,
        resizable: false,
        cellRenderer: this.profileType === 'list' ? this.pinRenderer : undefined,
        suppressKeyboardEvent: (params) => {
          const row = params.node.data as ProfileColumn | undefined
          if (!row) return false
          return this.onPinCellKeyDown(params.event, row, (selected) => {
            params.node.setSelected(selected)
          })
        },
      },
      { field: 'drag', headerName: '', rowDrag: true, width: 44, maxWidth: 44, sortable: false, filter: false, resizable: false },
      { field: 'column_name', hide: true },
      { field: 'display_name', headerName: 'Column Name', cellRenderer: this.columnRenderer },
      { field: 'derived_column', hide: true },
      { field: 'is_extra_data', hide: true },
      { field: 'id', hide: true },
      { field: 'name', hide: true },
      {
        field: 'order',
        headerName: this._translocoService.translate('Order'),
        width: 96,
        maxWidth: 120,
        filter: false,
        editable: (params) => (params.data as ProfileColumn).selected === true,
        cellEditor: 'agNumberCellEditor',
        cellEditorParams: () => ({ min: 1, max: this.rowData.filter((row) => row.selected).length, precision: 0 }),
        onCellValueChanged: (event) => {
          this.setColumnOrder(event.data as ProfileColumn, Number(event.newValue))
        },
      },
      { field: 'table_name', hide: true },
    ]
  }

  columnRenderer = (params: CellRendererParams) => {
    const value = params.value
    const { derived_column, is_extra_data } = params.data
    if (!derived_column && !is_extra_data) return value

    // add icon to extra data and derived columns
    const iconName = derived_column ? 'link' : is_extra_data ? 'emergency' : null
    const textSize = derived_column ? 'text-sm' : 'text-xs'

    const container = document.createElement('div')
    container.append(document.createTextNode(value))
    container.append(document.createTextNode(' '))

    const icon = document.createElement('span')
    icon.className = `material-icons align-middle ml-1 mb-2 text-secondary ${textSize}`
    icon.textContent = iconName
    container.append(icon)

    return container
  }

  pinRenderer = (params: ICellRendererParams<ProfileColumn>) => {
    const row = params.data
    if (!row) return ''

    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'flex h-8 w-full items-center justify-center'
    button.title = this._translocoService.translate(row.pinned ? 'Unpin column' : 'Pin column to the left')
    button.setAttribute('aria-label', button.title)
    button.setAttribute('aria-pressed', String(row.pinned))

    const icon = document.createElement('span')
    icon.className = `material-icons ${row.pinned ? 'text-primary-700' : 'text-secondary opacity-50'}`
    icon.textContent = 'push_pin'
    icon.setAttribute('aria-hidden', 'true')
    button.append(icon)

    button.addEventListener('click', (event) => {
      event.stopPropagation()
      const currentRow = params.node.data
      if (!currentRow) return
      this.togglePinned(currentRow, (selected) => {
        params.node.setSelected(selected)
      })
    })

    return button
  }

  onPinCellKeyDown(event: KeyboardEvent, row: ProfileColumn, setSelected: (selected: boolean) => void): boolean {
    if (event.key !== 'Enter' && event.key !== ' ') return false

    event.preventDefault()
    event.stopPropagation()
    this.togglePinned(row, setSelected)
    return true
  }

  togglePinned(row: ProfileColumn, setSelected: (selected: boolean) => void) {
    row.pinned = !row.pinned
    if (row.pinned) {
      row.selected = true
      setSelected(true)
    }

    const selectedIds = new Set(this.gridApi.getSelectedRows().map((selectedRow: ProfileColumn) => selectedRow.id))
    if (row.pinned) selectedIds.add(row.id)
    this.setRowData(selectedIds, this.rowData)
  }

  /**
   * Place selected rows (profile columns) at the top of the grid
   */
  setRowData(selectedColIds: Set<number>, profileColumns: ProfileColumnSettings[] = this.rowData) {
    let [selectedRows, unselectedRows]: [ProfileColumn[], ProfileColumn[]] = [[], []]

    const profileColumnById = new Map(profileColumns.map((column, index) => [column.id, { ...column, order: column.order ?? index + 1 }]))

    for (const col of this.columns) {
      const { column_name, derived_column, display_name, id, is_extra_data, name, table_name } = col
      const profileColumn = profileColumnById.get(id)
      const data = {
        column_name,
        display_name,
        derived_column: undefined,
        id,
        is_extra_data,
        name,
        order: undefined,
        pinned: undefined,
        selected: false,
        table_name,
      }

      if (derived_column) {
        data.derived_column = derived_column
      }

      if (selectedColIds.has(col.id)) {
        data.order = profileColumn?.order
        data.pinned = this.profileType === 'list' && profileColumn?.pinned === true
        data.selected = true
        selectedRows.push(data)
      } else {
        unselectedRows.push(data)
      }
    }

    selectedRows = selectedRows.sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
      return (a.order ?? Number.MAX_SAFE_INTEGER) - (b.order ?? Number.MAX_SAFE_INTEGER) || naturalSort(a.display_name, b.display_name)
    })
    unselectedRows = unselectedRows.sort((a, b) => naturalSort(a.display_name, b.display_name))
    let order = 0
    this.rowData = [...selectedRows, ...unselectedRows].map((row) => ({
      ...row,
      order: row.selected ? ++order : undefined,
    }))

    if (this.gridApi) {
      clearTimeout(this._selectionTimer)
      this._selectionTimer = setTimeout(() => {
        this.setSelectedRows()
      }, 0)
    }
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.sizeColumnsToFit()
    this.setSelectedRows()

    // this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  setSelectedRows() {
    this.gridApi.forEachNode((node) => {
      node.setSelected((node.data as ProfileColumn).selected === true)
    })
  }

  onRowSelected(event: RowSelectedEvent) {
    // Ignore programmatic selection and header checkbox intermediate events
    if (event.source === 'api') return

    const row = event.data as ProfileColumn
    row.selected = event.node.isSelected() === true
    if (!row.selected) row.pinned = false

    // Defer to let AG Grid finish processing all row selections (e.g., header checkbox "select all")
    if (this._rowSelectedTimer) clearTimeout(this._rowSelectedTimer)
    this._rowSelectedTimer = setTimeout(() => {
      const selectedRows = new Set(this.gridApi.getSelectedRows().map((r: ProfileColumn) => r.id))
      this.setRowData(selectedRows, this.rowData)
    }, 50)
  }

  onRowDragEnd() {
    const visibleRows: ProfileColumn[] = []
    this.gridApi.forEachNodeAfterFilterAndSort((node) => {
      if (node.data) visibleRows.push(node.data as ProfileColumn)
    })

    const visibleIds = new Set(visibleRows.map((row) => row.id))
    let nextVisibleRow = 0
    const orderedRows = this.rowData.map((row) => (visibleIds.has(row.id) ? visibleRows[nextVisibleRow++] : row))
    let order = 0
    const profileColumns = orderedRows.map((row) => (row.selected ? { ...row, order: ++order } : row))
    const selectedIds = new Set(this.gridApi.getSelectedRows().map((row: ProfileColumn) => row.id))
    this.setRowData(selectedIds, profileColumns)
  }

  setColumnOrder(column: ProfileColumn, requestedOrder: number) {
    const selectedRows = this.rowData.filter((row) => row.selected && row.id !== column.id)
    const order = Number.isFinite(requestedOrder) ? Math.trunc(requestedOrder) : 1
    selectedRows.splice(Math.max(0, Math.min(order - 1, selectedRows.length)), 0, column)
    const profileColumns = selectedRows.map((row, index) => ({ ...row, order: index + 1 }))
    this.setRowData(new Set(selectedRows.map((row) => row.id)), profileColumns)
  }

  selectProfile(event: MatSelectChange) {
    clearTimeout(this._rowSelectedTimer)
    const profileId: number = event.value as number
    const profile = this.profiles.find((p) => p.id === profileId)
    this.currentUser.settings.profile[this.profileType][this.type] = profileId
    this.currentProfile = profile
    this.setRowData(new Set(profile.columns.map((c) => c.id)), profile.columns)
    this.updateOrgUserSettings$.next()
  }

  openDeleteModal() {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Column List Profile', instance: this.currentProfile.name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap(() => {
          console.log('DEVELOPER NOTE: Delete function fails while in development mode, via a vite proxy error')
        }),
        switchMap(() => this._inventoryService.deleteColumnListProfile(this.orgId, this.currentProfile.id)),
        tap(() => {
          this.initPage()
        }),
      )
      .subscribe()
  }

  openProfileModal(mode: ProfileModalMode, columns: ProfileColumn[] = []) {
    const profile = mode === 'create' ? null : this.currentProfile
    const dialogRef = this._dialog.open(ModalComponent, {
      width: '40rem',
      data: {
        columns,
        cycleId: null,
        inventoryType: this.type,
        location: this.profileLocation,
        mode,
        orgId: this.orgId,
        profile,
        profiles: this.profiles,
        type: this.type === 'taxlots' ? 'Tax Lot' : 'Property',
      },
    })

    let newProfileId: number

    dialogRef
      .afterClosed()
      .pipe(
        filter((id: number) => {
          newProfileId = id
          return !!id
        }),
        switchMap(() => this._inventoryService.getColumnListProfiles(this.profileLocation, this.type)),
        tap((profiles) => {
          this.profiles = profiles.filter((p) => p.inventory_type === this.displayType)
          this.currentProfile = this.profiles.find((p) => p.id === newProfileId) ?? this.profiles[0] ?? null
          this.currentUser.settings.profile[this.profileType][this.type] = this.currentProfile?.id
          this.setGrid()
        }),
        switchMap(() => this.updateOrgUserSettings()),
      )
      .subscribe()
  }

  onSave = () => {
    this.gridApi?.stopEditing()
    if (!this.currentProfile) {
      this.openProfileModal('create', this.getSelectedProfileColumns())
      return
    }

    const data = { ...this.currentProfile, columns: this.getSelectedProfileColumns() }
    this.updateCLP$.next(data)
  }

  getSelectedProfileColumns(): ProfileColumn[] {
    return this.rowData
      .filter((row) => row.selected)
      .map((row, index) => ({ ...row, order: index + 1, pinned: this.profileType === 'list' && row.pinned }))
  }

  ngOnDestroy(): void {
    clearTimeout(this._rowSelectedTimer)
    clearTimeout(this._selectionTimer)
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
