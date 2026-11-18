import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, FirstDataRenderedEvent, GridApi, GridReadyEvent } from 'ag-grid-community'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import { finalize, map, Subject, tap } from 'rxjs'
import type { Column, CurrentUser, GenericColumn, OrganizationUserSettings } from '@seed/api'
import { InventoryService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType, Profile, ProfileColumn, ValueGetterParamsData, ViewResponse } from 'app/modules/inventory/inventory.types'
import { EditStateModalComponent } from '../modal/edit-state.component'

ModuleRegistry.registerModules([AllCommunityModule])

type CellRendererParams = { value: string; data: { derived_column: number; is_extra_data: boolean } }
@Component({
  selector: 'seed-inventory-detail-history',
  templateUrl: './history-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports],
})
export class HistoryGridComponent implements OnChanges, OnDestroy {
  @Input() columns: Column[]
  @Input() currentUser: CurrentUser
  @Input() currentProfile: Profile
  @Input() matchingColumns: string[]
  @Input() orgId: number
  @Input() profiles: Profile[]
  @Input() type: InventoryType
  @Input() view: ViewResponse
  @Input() viewId: number
  @Output() refreshView = new EventEmitter<null>()
  private _configService = inject(ConfigService)
  private _dialog = inject(MatDialog)
  private _inventoryService = inject(InventoryService)
  private _router = inject(Router)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  columnDefs: ColDef[]
  derivedColumnNames: Set<string>
  extraDataColumnNames: Set<string>
  gridApi: GridApi
  gridColumns: (Column | ProfileColumn)[]
  gridTheme$ = this._configService.gridTheme$.pipe(map((t) => t.withParams({ oddRowBackgroundColor: 'rgba(0,0,0,0.04)' })))
  loading = false
  orgUserId: number
  rowData: Record<string, unknown>[]
  userSettings: OrganizationUserSettings

  defaultProfile = {
    detail: { taxlots: null, properties: null },
    list: { taxlots: null, properties: null },
  }

  defaultColDef = {
    sortable: false,
    filter: false,
    resizable: true,
    suppressMovable: true,
    minWidth: 100,
  }

  getHistory() {
    this.setGridColumns()
    this.setColumnDefs()
    this.setRowData()
  }

  /*
   * 1. find current profile
   * 2. if no profile, set to null
   * 3. set columns to current profile columns or all canonical columns
   */
  setGridColumns() {
    if (this.currentProfile?.columns) {
      this.gridColumns = this.currentProfile.columns
    } else {
      this.gridColumns = this.columns.filter((c) => !c.is_extra_data)
    }
    this.derivedColumnNames = new Set(this.columns.filter((c) => c.derived_column).map((c) => c.column_name))
    this.extraDataColumnNames = new Set(this.columns.filter((c) => c.is_extra_data).map((c) => c.column_name))
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.view || changes.currentProfile) {
      this.getHistory()
    }
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi = params.api
  }

  onFirstDataRendered(params: FirstDataRenderedEvent) {
    params.api.sizeColumnsToFit()
  }

  get gridHeight() {
    if (!this.rowData) return
    return Math.min(this.rowData?.length * 70, 500)
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'field', headerName: 'Field', pinned: true, cellRenderer: this.fieldRenderer },
      { field: 'state', headerName: 'Main' },
      { field: 'derived_column', hide: true },
      { field: 'is_extra_data', hide: true },
    ]

    for (const { filename } of this.view.history) {
      // field names with periods require formatting, otherwise treated as a path
      this.columnDefs.push({
        field: filename,
        headerName: filename,
        valueGetter: (params: ValueGetterParamsData) => params.data[filename],
      })
    }
  }

  fieldRenderer = (params: CellRendererParams) => {
    const value = params.value
    const { derived_column, is_extra_data } = params.data
    if (!derived_column && !is_extra_data) return value

    // add icon to extra data and derived columns
    const iconName = derived_column ? 'link' : is_extra_data ? 'emergency' : null
    const textSize = derived_column ? 'text-sm' : 'text-xs'
    return `${value} <span class="material-icons align-middle ml-1 mb-2 text-secondary ${textSize}">${iconName}</span>`
  }

  setRowData() {
    // Transposed data. Each row is a column name (address line 1, address line 2, etc.)
    this.rowData = []
    const columnsSorted: GenericColumn[] = this.gridColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))

    for (const { column_name, display_name } of columnsSorted) {
      const isExtraData = this.extraDataColumnNames.has(column_name)
      const isDerived = this.derivedColumnNames.has(column_name)
      let value = isExtraData ? this.view.state.extra_data[column_name] : this.view.state[column_name]
      const row = { field: display_name, state: value, is_extra_data: isExtraData, derived_column: isDerived }
      for (const item of this.view.history) {
        value = isExtraData ? item.state.extra_data[column_name] : item.state[column_name]
        row[item.filename] = value
      }
      this.rowData.push(row)
    }
  }

  editMain() {
    const dialogRef = this._dialog.open(EditStateModalComponent, {
      autoFocus: false,
      disableClose: true,
      width: '50rem',
      maxHeight: '75vh',
      data: {
        columns: this.gridColumns,
        orgId: this.orgId,
        view: this.view,
        matchingColumns: this.matchingColumns,
        extraDataColumnNames: this.extraDataColumnNames,
      },
      panelClass: 'seed-dialog-panel',
    })

    dialogRef
      .afterClosed()
      .pipe(
        tap((updatedFields: Record<string, unknown>) => {
          if (this.updatedFieldsEmpty(updatedFields)) {
            this._snackBar.info('No changes detected')
          } else if (updatedFields) {
            this.saveItem(updatedFields)
          }
        }),
      )
      .subscribe()
  }

  updatedFieldsEmpty(updatedFields) {
    return JSON.stringify(updatedFields) === JSON.stringify({ extra_data: {} })
  }

  /*
   * save the user's changes to the Property/TaxLot State object.
   */
  saveItem(updatedFields: Record<string, unknown>) {
    // const updatedFields = this.checkStateDifference(this.view.state, this.viewCopy.state)
    this.loading = true
    this._inventoryService
      .updateInventory(this.orgId, this.viewId, this.type, updatedFields)
      .pipe(
        tap((response) => {
          if (response.view_id !== this.viewId) {
            void this._router.navigateByUrl(`${this.type}/${response.view_id}`)
          } else {
            this.refreshView.emit()
          }
        }),
        finalize(() => {
          this.loading = false
        }),
      )
      .subscribe()
  }

  checkExtraDataDifference(
    extraData: Record<string, unknown>,
    extraDataCopy: Record<string, unknown>,
    updatedFields: Record<string, unknown>,
  ) {
    for (const field in extraData) {
      if (extraData[field] !== extraDataCopy[field]) {
        updatedFields[field] = extraData[field]
      }
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
