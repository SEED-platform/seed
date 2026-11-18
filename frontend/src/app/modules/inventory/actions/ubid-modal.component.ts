import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, CellValueChangedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import { filter, finalize, forkJoin, map, of, Subject, switchMap, take, tap } from 'rxjs'
import type { Ubid } from '@seed/api'
import { InventoryService, UbidService } from '@seed/api'
import { AlertComponent, ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType, InventoryTypeSingular, ViewResponse } from '../inventory.types'

@Component({
  selector: 'seed-ubid-modal',
  templateUrl: './ubid-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AlertComponent, CommonModule, MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class UbidModalComponent implements OnInit, OnDestroy {
  private _configService = inject(ConfigService)
  private _dialogRef = inject(MatDialogRef<UbidModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _ubidService = inject(UbidService)
  private _unsubscribeAll$ = new Subject<void>()

  gridTheme$ = this._configService.gridTheme$
  stateId: number
  viewId: number
  ubid: string
  ubids: Ubid[] = []
  view: ViewResponse
  gridApi: GridApi
  colDefs: ColDef[] = []
  gridHeight = 0
  gridOptions = {
    singleClickEdit: true,
  }
  ubidsToDelete: number[] = []
  originalUbids: Ubid[] = []
  errMessages: string[] = []
  inProgress = false
  singularType: InventoryTypeSingular

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    type: InventoryType;
  }

  ngOnInit(): void {
    this.viewId = this.data.viewIds[0]
    this.singularType = this.data.type === 'taxlots' ? 'taxlot' : 'property'
    this.getUbids()
  }

  getUbids() {
    const { orgId, type } = this.data
    forkJoin({
      view: this._inventoryService.getView(orgId, this.viewId, type),
      ubids: this._ubidService.getUbidModelsByView(orgId, this.viewId, type),
    })
      .pipe(
        tap(({ view, ubids }) => {
          this.view = view
          this.stateId = view.state.id
          this.ubids = ubids
          this.originalUbids = ubids
          this.setGrid()
        }),
      )
      .subscribe()
  }

  setGrid() {
    // assume all incoming ubids are valid
    this.ubids = this.ubids.map((u) => ({ ...u, valid: true }))
    this.getGridHeight()
    this.colDefs = [
      {
        field: 'ubid',
        headerName: 'UBID',
        flex: 1,
        editable: true,
        cellRenderer: this.ubidRenderer,
      },
      {
        field: 'preferred',
        headerName: 'Preferred',
        flex: 0.5,
        editable: true,
        onCellValueChanged: this.onPreferredChange,
      },
      {
        field: 'delete',
        headerName: 'Delete',
        flex: 0.5,
        cellRenderer: this.deleteRenderer,
      },
    ]
  }

  getGridHeight() {
    const rowLength = this.ubids.length || 1
    this.gridHeight = Math.min(rowLength * 42 + 50, 400)
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'delete') return
    const { id } = event.data as { id: number }
    const index = event.rowIndex

    // store id to delete and remove row
    if (id) this.ubidsToDelete.push(id)
    this.ubids.splice(index, 1)
    this.ubids = [...this.ubids]
    this.getGridHeight()
  }

  ubidRenderer = ({ value }) => {
    return `
      <div>${value}</div>
    `
  }

  deleteRenderer = () => {
    return `
      <div class="mt-2">
        <span class="material-icons cursor-pointer text-secondary" title="Delete" data-action="delete">clear</span>
      </div>
    `
  }

  onPreferredChange = (params: CellValueChangedEvent<{ preferred: boolean }>) => {
    if (params.newValue) {
      params.api.forEachNode((node) => {
        if (node.id !== params.node.id && node.data.preferred) {
          node.setDataValue('preferred', false)
        }
      })
    }
  }

  addRow() {
    const newUbid = {
      ubid: '',
      preferred: false,
    } as Ubid
    if (this.data.type === 'taxlots') {
      newUbid.taxlot = this.stateId
    } else {
      newUbid.property = this.stateId
    }
    this.ubids = [...this.ubids, newUbid]
    this.getGridHeight()
  }

  onSubmit() {
    // stop editing
    // clear empty ubids
    // delete
    // check validity
    // update old ones
    // create new ones
    // save others
    this.errMessages = []
    this.gridApi.stopEditing()
    this.ubids = this.ubids.filter((u) => u.ubid)
    this.inProgress = true

    this.validateNewUbids()
      .pipe(
        filter(Boolean),
        switchMap(() => this.CreateUpdateDeleteUbid()),
        tap(() => {
          this.close(true)
        }),
        finalize(() => {
          this.inProgress = false
        }),
      )
      .subscribe()
  }

  validateNewUbids() {
    const ubidStrings = this.ubids.map((u) => u.ubid?.trim()).filter(Boolean)
    const duplicateUbidStrings = new Set<string>()
    const seenUbidStrings = new Set<string>()

    for (const ubid of ubidStrings) {
      if (seenUbidStrings.has(ubid)) duplicateUbidStrings.add(ubid)
      seenUbidStrings.add(ubid)
    }

    if (duplicateUbidStrings.size) {
      for (const ubid of duplicateUbidStrings) {
        this.errMessages.push(`UBID ${ubid} already exists`)
      }
      return of(false)
    }

    const originalUbidStrings = new Set(this.originalUbids.map((u) => u.ubid))
    const ubidsToValidate = [...seenUbidStrings].filter((ubid) => !originalUbidStrings.has(ubid))
    if (!ubidsToValidate.length) return of(true)

    return forkJoin(ubidsToValidate.map((ubid) => this._ubidService.validate(this.data.orgId, ubid))).pipe(
      tap((response) => {
        for (const [index, validity] of response.entries()) {
          if (!validity) {
            this.errMessages.push(`UBID ${ubidsToValidate[index]} is invalid`)
          }
        }
      }),
      map((response) => response.every((v) => v)),
      take(1),
    )
  }

  CreateUpdateDeleteUbid() {
    const { orgId, type } = this.data
    const createUbids = this.ubids.filter((u) => !u.id)
    const updateUbids = this.getUpdateUbids()

    const createDetails = (ubid: Ubid) => ({ ubid: ubid.ubid, preferred: ubid.preferred, [this.singularType]: this.stateId })
    const updateDetails = (ubid: Ubid) => ({ ubid: ubid.ubid, preferred: ubid.preferred })

    const createRequests = createUbids.map((ubid) => this._ubidService.create(orgId, this.viewId, createDetails(ubid), type))
    const updateRequests = updateUbids.map((ubid) => this._ubidService.update(orgId, this.viewId, ubid.id, updateDetails(ubid), type))
    const deleteRequests = this.ubidsToDelete.map((id) => this._ubidService.delete(this.data.orgId, this.viewId, id, this.data.type))

    const requests = [...deleteRequests, ...createRequests, ...updateRequests]

    return requests.length ? forkJoin(requests) : of(null)
  }

  getUpdateUbids() {
    return this.ubids.filter((ubid) => {
      if (!ubid.id) return
      const oldUbid = this.originalUbids.find((u) => u.id === ubid.id)
      return oldUbid ? oldUbid.preferred !== ubid.preferred || oldUbid.ubid !== ubid.ubid : false
    })
  }

  close(success = false) {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
