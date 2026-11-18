import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import { combineLatest, filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Cycle, Dataset } from '@seed/api'
import { CycleService, DatasetService, UserService } from '@seed/api'
import { DeleteModalComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { DataUploadModalComponent } from './data-upload/data-upload-modal.component'
import { MeterDataUploadModalComponent } from './data-upload/meter-upload-modal.component'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-data',
  templateUrl: './datasets.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, PageComponent],
})
export class DatasetsComponent implements OnDestroy, OnInit {
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _datasetService = inject(DatasetService)
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _userService = inject(UserService)
  private _dialog = inject(MatDialog)
  private readonly _unsubscribeAll$ = new Subject<void>()
  columnDefs: ColDef[]
  cycles: Cycle[] = []
  datasets: Dataset[]
  datasetsColumns = ['name', 'importfiles', 'updated_at', 'last_modified_by', 'actions']
  existingNames: string[] = []
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  orgId: number
  // Set via the '?create=true' query param (e.g. linked from the dashboard) to auto-open the create dataset dialog
  private _openCreateOnLoad = false

  ngOnInit(): void {
    // Rerun resolver and initializer on org change
    // this._userService.currentOrganizationId$.pipe(skip(1)).subscribe(() => {
    //   from(this._router.navigate([this._router.url])).subscribe(() => {
    //     this._init()
    //   })
    // })

    this._openCreateOnLoad = this._route.snapshot.queryParamMap.get('create') === 'true'

    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.orgId = orgId
          this._datasetService.list(orgId)
        }),
        switchMap(() => combineLatest([this._cycleService.cycles$, this._datasetService.datasets$])),
        tap(([cycles, datasets]) => {
          this.cycles = cycles
          this.datasets = datasets.sort((a, b) => naturalSort(a.name, b.name))
          this.existingNames = datasets.map((ds) => ds.name)
          this.setColumnDefs()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        if (this._openCreateOnLoad) {
          this._openCreateOnLoad = false
          void this._router.navigate([], { relativeTo: this._route, queryParams: {}, replaceUrl: true })
          this.createDataset()
        }
      })
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'id', hide: true },
      { field: 'name', headerName: 'Name', cellRenderer: this.nameRenderer },
      { field: 'importfiles', headerName: 'Files', flex: 0.5, valueGetter: ({ data }: { data: Dataset }) => data.importfiles.length },
      {
        field: 'updated_at',
        headerName: 'Updated At',
        flex: 0.5,
        minWidth: 180,
        valueFormatter: ({ value }: { value: string }) => (value ? new Date(value).toLocaleString() : ''),
        comparator: (a: string, b: string) => this.toTimestamp(a) - this.toTimestamp(b),
      },
      { field: 'last_modified_by', headerName: 'Last Modified By' },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionsRenderer, flex: 1 },
    ]
  }

  // Sort by the full timestamp (not the display string), treating missing/invalid dates as oldest
  toTimestamp(value: string): number {
    const time = value ? new Date(value).getTime() : NaN
    return Number.isNaN(time) ? 0 : time
  }

  nameRenderer({ value }: { value: string }) {
    return `
      <div class="text-primary dark:text-primary-300 cursor-pointer" title="Dataset Detail" data-action="detail">
        ${value}
        <span class="material-icons text-secondary text-sm">open_in_new</span>
      </div>
    `
  }

  actionsRenderer() {
    return `
      <div class="flex gap-2 align-center">
      <span class="inline-flex items-center gap-1 cursor-pointer border rounded-full bg-primary text-white h-8 mt-1 px-3 hover:bg-primary-800" title="Add Data Files" data-action="addDataFiles">
        <span class="material-icons text-base">add</span>
        <span class="text-sm">Data Files</span>
      </span>
      <span class="inline-flex items-center gap-1 cursor-pointer border rounded-full h-8 mt-1 px-3 hover:bg-gray-400" title="Add Meter Data" data-action="addMeterData">
        <span class="material-icons text-base">add</span>
        <span class="text-sm">Meter Data</span>
      </span>
      <span class="material-icons cursor-pointer text-cyan-600 my-auto" title="Rename Dataset" data-action="rename">edit</span>
      <span class="material-icons cursor-pointer text-red-500 my-auto" title="Delete Dataset" data-action="delete">delete</span>
      </div>
    `
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.sizeColumnsToFit()
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (!['actions', 'name'].includes(event.colDef.field)) return

    const target = event.event.target as HTMLElement
    const action = target.closest('[data-action]')?.getAttribute('data-action')
    const { id } = event.data as { id: number }
    const dataset = this.datasets.find((ds) => ds.id === id)

    if (action === 'addDataFiles' && this.cycles.length) {
      this._dialog.open(DataUploadModalComponent, {
        width: '40rem',
        data: { orgId: this.orgId, dataset, cycles: this.cycles },
      })
    } else if (action === 'addMeterData' && this.cycles.length) {
      this._dialog.open(MeterDataUploadModalComponent, {
        width: '60rem',
        data: { orgId: this.orgId, datasetId: dataset.id, cycleId: this.cycles[0].id, file: null },
      })
    } else if (action === 'rename') {
      this.editDataset(dataset)
    } else if (action === 'delete') {
      this.deleteDataset(dataset)
    } else if (action === 'detail') {
      void this._router.navigate([`/data/${id}`])
    }
  }

  editDataset(dataset: Dataset) {
    const existingNames = this.existingNames.filter((n) => n !== dataset.name)
    this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, dataset, existingNames },
    })
  }

  deleteDataset(dataset: Dataset) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Dataset', instance: dataset.name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._datasetService.delete(this.orgId, dataset.id)),
      )
      .subscribe()
  }

  createDataset = () => {
    this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, dataset: null, existingNames: this.existingNames },
    })
  }

  trackByFn(_index: number, { id }: Dataset) {
    return id
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
