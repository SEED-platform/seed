import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Ubid } from '@seed/api'
import { InventoryService, OrganizationService, UbidService, UserService } from '@seed/api'
import { DeleteModalComponent, NotFoundComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType, ViewResponse } from 'app/modules/inventory/inventory.types'
import { MapComponent } from '../detail'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-inventory-detail-ubids',
  templateUrl: './ubids.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MapComponent, MaterialImports, NotFoundComponent, PageComponent],
})
export class UbidsComponent implements OnDestroy, OnInit {
  @ViewChild(MapComponent) mapComponent!: MapComponent
  private _configService = inject(ConfigService)
  private _dialog = inject(MatDialog)
  private _inventoryService = inject(InventoryService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private _ubidService = inject(UbidService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  columnDefs: ColDef[]
  gridApi: GridApi
  gridHeight = 0
  gridTheme$ = this._configService.gridTheme$
  enableMap = false
  rowData: Record<string, unknown>[] = []
  orgId: number
  type: InventoryType
  ubids: Ubid[]
  view: ViewResponse
  viewId: number
  viewDisplayField$: Observable<string>

  ngOnInit() {
    this.getUrlParams()
      .pipe(
        tap(() => {
          this.getStreams()
        }),
      )
      .subscribe()
  }

  getUrlParams() {
    return this._route.parent.paramMap.pipe(
      tap((params) => {
        this.viewId = parseInt(params.get('id'))
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.viewId, 'properties')
        this.type = params.get('type') as InventoryType
      }),
    )
  }

  getStreams() {
    this._inventoryService.view$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        tap((view) => {
          this.view = view
          setTimeout(() => {
            this.enableMap = Boolean(this.view.state.ubid && this.view.state.bounding_box && this.view.state.centroid)
            this.mapComponent?.initMap()
          })
        }),
      )
      .subscribe()

    this._userService.currentOrganizationId$.subscribe((orgId) => (this.orgId = orgId))
    this._ubidService.ubids$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        tap((ubids) => {
          ubids.sort((a, b) => Number(b.preferred) - Number(a.preferred))
          this.ubids = ubids
          this.setGrid()
        }),
      )
      .subscribe()
  }

  setGrid() {
    this.setColumnDefs()
    this.setRowData()
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'id', hide: true },
      { field: 'property', hide: true },
      { field: 'taxlot', hide: true },
      { field: 'ubid', headerName: 'UBID' },
      { field: 'preferred', headerName: 'Preferred', cellRenderer: this.preferredRenderer },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionRenderer },
    ]
  }

  preferredRenderer({ value }: { value: boolean }) {
    if (!value) return ''

    return `
      <div class="flex gap-2 mt-2 align-center">
        <span class="material-icons cursor-pointer text-secondary">check_circle</span>
      </div>
    `
  }

  actionRenderer = () => {
    return `
      <div class="flex gap-2 mt-2 align-center">
        <span class="material-icons cursor-pointer text-secondary" data-action="edit">edit</span>
        <span class="material-icons cursor-pointer text-secondary" data-action="delete">clear</span>
      </div>
    `
  }

  setRowData() {
    this.rowData = this.ubids
    this.gridHeight = this.rowData.length * 42 + 50
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.sizeColumnsToFit()
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'actions') return

    const target = event.event.target as HTMLElement
    const action = target.getAttribute('data-action')

    if (action === 'edit') {
      this.editUbid(event.data as Ubid)
    } else if (action === 'delete') {
      this.deleteUbid(event.data as Ubid)
    }
  }

  getRowClass = ({ data }: { data: Ubid }) => {
    return data.preferred ? 'bg-primary text-white' : ''
  }

  createUbid = () => {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: {
        orgId: this.orgId,
        viewId: this.viewId,
        stateId: this.view.state.id,
        ubid: null,
        type: this.type,
        existingUbids: this.ubids.map((u) => u.ubid),
      },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._inventoryService.getView(this.orgId, this.viewId, this.type)),
      )
      .subscribe()
  }

  editUbid(ubid: Ubid) {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: {
        orgId: this.orgId,
        viewId: this.viewId,
        stateId: this.view.state.id,
        ubid,
        type: this.type,
        existingUbids: this.ubids.filter((u) => u.id !== ubid.id).map((u) => u.ubid),
      },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._inventoryService.getView(this.orgId, this.viewId, this.type)),
      )
      .subscribe()
  }

  deleteUbid(ubid: Ubid) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'UBID', instance: ubid.ubid },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._ubidService.delete(this.orgId, this.viewId, ubid.id, this.type)),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
