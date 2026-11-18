import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import type { MatDialogRef } from '@angular/material/dialog'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { InventoryGroup } from '@seed/api'
import { GroupsService, OrganizationService } from '@seed/api'
import { DeleteModalComponent, NotFoundComponent, PageComponent } from '@seed/components'
import { ConfigService } from '@seed/services'
import type { InventoryType } from 'app/modules/inventory/inventory.types'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-inventory-list-groups',
  templateUrl: './groups.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, NotFoundComponent, PageComponent],
})
export class GroupsComponent implements OnDestroy, OnInit {
  private _configService = inject(ConfigService)
  private _dialog = inject(MatDialog)
  private _groupsService = inject(GroupsService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private readonly _unsubscribeAll$ = new Subject<void>()

  columnDefs: ColDef[] = []
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  groups: InventoryGroup[]
  orgId: number
  rowData: Record<string, unknown>[] = []
  type = this._route.snapshot.paramMap.get('type') as InventoryType

  ngOnInit(): void {
    this.initPage()
  }

  initPage() {
    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(({ org_id }) => this.getDependencies(org_id)),
        tap(() => {
          this.setGrid()
        }),
      )
      .subscribe()
  }

  getDependencies(orgId: number): Observable<unknown> {
    this.orgId = orgId
    this._groupsService.list(orgId)

    return this._groupsService.groups$.pipe(
      tap((groups: InventoryGroup[]) => {
        this.groups = groups
      }),
    )
  }

  setGrid() {
    this.setColumnDefs()
    this.setRowData()
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'id', hide: true },
      { field: 'name', headerName: 'Name', cellRenderer: this.nameRenderer },
      { field: 'access_level_instance', headerName: 'Access Level Instance' },
      { field: 'inventory_count', headerName: 'Inventory Count' },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionRenderer },
    ]
  }

  nameRenderer = ({ value }: { data: InventoryGroup; value: string }) => {
    return `<span class="underline text-primary dark:text-primary-500 cursor-pointer" data-action="navigate">${value}</span>`
  }

  actionRenderer = () => {
    return `
      <div class="flex gap-2 mt-2 align-center">
        <span class="material-icons cursor-pointer text-cyan-600" title="Edit" data-action="edit">edit</span>
        <span class="material-icons cursor-pointer text-red-700" title="Delete" data-action="delete">delete</span>
      </div>
    `
  }

  setRowData() {
    this.rowData = []
    for (const group of this.groups ?? []) {
      const row = {
        id: group.id,
        name: group.name,
        access_level_instance: group.access_level_instance_data.name,
        inventory_count: group.inventory_list.length,
      }
      this.rowData.push(row)
    }
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.sizeColumnsToFit()
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  get gridHeight() {
    return Math.min(this.rowData.length * 42 + 50, 1000)
  }

  onCellClicked(event: CellClickedEvent) {
    const target = event.event.target as HTMLElement
    const action = target.closest('[data-action]')?.getAttribute('data-action')
    const { id, name } = event.data as { id: number; name: string }

    if (action === 'navigate') {
      void this._router.navigate([`/${this.type}/groups`, id])
    } else if (action === 'edit') {
      this.editGroup(id)
    } else if (action === 'delete') {
      this.openDeleteModal(id, name)
    }
  }

  createGroup = () => {
    const data = { id: null, group: null, groups: this.groups, mode: 'create', orgId: this.orgId }
    this.openGroupModal(data)
  }

  editGroup(id: number) {
    const group = this.groups.find((g) => g.id === id)
    const data = { id, group, groups: this.groups, mode: 'edit', orgId: this.orgId }
    this.openGroupModal(data)
  }

  openGroupModal(data: Record<string, unknown>) {
    const dialogRef: MatDialogRef<FormModalComponent, boolean> = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data,
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap(() => {
          this.initPage()
        }),
      )
      .subscribe()
  }

  openDeleteModal(id: number, name: string) {
    const dialogRef: MatDialogRef<DeleteModalComponent, boolean> = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Group', instance: name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap(() => {
          console.log('DEVELOPER NOTE: Delete function fails while in development mode, via a vite proxy error')
        }),
        switchMap(() => this._groupsService.delete(this.orgId, id)),
        tap(() => {
          this.initPage()
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
