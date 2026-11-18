import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, GridApi, GridOptions, GridReadyEvent } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { catchError, combineLatest, EMPTY, of, Subject, take, tap } from 'rxjs'
import type { Column } from '@seed/api'
import { InventoryService, MappableColumnService, MatchingService } from '@seed/api'
import { AlertComponent, ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { FilterResponse, InventoryType, State } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-merge-modal',
  templateUrl: './merge-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AlertComponent, CommonModule, MaterialImports, ModalHeaderComponent, ProgressBarComponent, SharedImports],
})
export class MergeModalComponent implements OnInit, OnDestroy {
  private _configService = inject(ConfigService)
  private _dialogRef = inject(MatDialogRef<MergeModalComponent>)
  private _matchingService = inject(MatchingService)
  private _mappableColumnService = inject(MappableColumnService)
  private _inventoryService = inject(InventoryService)
  private _unsubscribeAll$ = new Subject<void>()
  colDefs: ColDef[] = []
  columns: Column[] = []
  errorMessage: string = null
  gridHeight = 400
  gridOptions: GridOptions = { rowDragManaged: true }
  gridTheme$ = this._configService.gridTheme$
  inventory: FilterResponse
  loading: boolean
  matchingColumnDisplayNames: string[] = []
  metersExist = false
  postData: Record<string, unknown>[] = []
  preData: State[] = []
  preGridApi: GridApi
  results: string[] = []
  status: 'loading' | 'review' | 'confirm' | 'complete' | 'error' = 'loading'
  title = 'Merge Inventory'

  data = inject(MAT_DIALOG_DATA) as {
    cycleId: number;
    orgId: number;
    profileId: number;
    viewIds: number[];
    type: InventoryType;
  }

  ngOnInit(): void {
    const { orgId, viewIds } = this.data
    const metersExist$ = this.data.type === 'properties' ? this._inventoryService.propertiesMetersExist(orgId, viewIds) : of(false)
    const columns$
      = this.data.type === 'taxlots'
        ? this._mappableColumnService.getTaxLotColumns(orgId)
        : this._mappableColumnService.getPropertyColumns(orgId)
    const inventory$ = this.getInventory$()

    combineLatest([metersExist$, columns$, inventory$])
      .pipe(
        take(1),
        tap(([metersExist, columns, inventory]) => {
          this.metersExist = metersExist
          this.columns = columns
          this.matchingColumnDisplayNames = this.columns.filter((c) => c.is_matching_criteria).map((c) => c.display_name)
          this.inventory = inventory
          this.setGrid()
          this.status = 'review'
        }),
      )
      .subscribe()
  }

  getInventory$(): Observable<FilterResponse> {
    const { cycleId, orgId, profileId, viewIds } = this.data
    const inventory_type = this.data.type === 'taxlots' ? 'taxlot' : 'property'
    const params = new URLSearchParams({
      cycle: cycleId.toString(),
      ids_only: 'false',
      include_related: 'true',
      inventory_type,
      organization_id: orgId.toString(),
      page: '1',
      per_page: '999999999',
    })

    const data = {
      include_property_ids: null,
      profile_id: profileId,
      include_view_ids: viewIds,
    }

    return this._inventoryService.getAgInventory(params.toString(), data)
  }

  setGrid() {
    this.preData = this.inventory.results as State[]
    this.gridHeight = Math.min(this.preData.length * 35 + 43, 500)
    const dragRow: ColDef = { field: 'Drag', rowDrag: true, resizable: false, width: 70, pinned: 'left' }
    this.colDefs = [dragRow, ...this.inventory.column_defs]
    this.postData = [this.preData[0]]
  }

  onPreGridReady(agGrid: GridReadyEvent) {
    this.preGridApi = agGrid.api
  }

  onRowDragEnd() {
    const firstRow = this.preGridApi.getDisplayedRowAtIndex(0)
    this.postData = [firstRow.data] as State[]
  }

  onSubmit() {
    this.status = 'confirm'
    this.title = 'Are you sure you want to continue?'
  }

  onConfirm() {
    const { orgId, type } = this.data
    const viewIds = this.getOrderedViewIds()
    const singularType = type === 'taxlots' ? 'tax lot' : 'property'
    this._matchingService
      .mergeInventory(orgId, viewIds, type)
      .pipe(
        tap(({ match_link_count, match_merged_count }) => {
          this.results = [
            `Resulting ${singularType} has ${match_link_count} cross cycle links`,
            `${match_merged_count} subsequent ${type} merged`,
          ]
          this.status = 'complete'
          this.title = 'Merge Complete'
        }),
        catchError(({ message }) => {
          this.errorMessage = message as string
          this.status = 'error'
          return EMPTY
        }),
      )
      .subscribe()
  }

  getOrderedViewIds(): number[] {
    const orderedViewIds: number[] = []

    this.preGridApi?.forEachNodeAfterFilterAndSort((node) => {
      const state = node.data as State | undefined
      const viewId = this.data.type === 'taxlots' ? state?.taxlot_view_id : state?.property_view_id
      if (viewId) orderedViewIds.push(viewId)
    })

    // Legacy merge order is bottom-to-top; reverse the displayed top-to-bottom order.
    return orderedViewIds.length ? orderedViewIds.toReversed() : [...this.data.viewIds]
  }

  close(success = false): void {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
