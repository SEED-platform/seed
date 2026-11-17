import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { filter, of, Subject, switchMap, tap } from 'rxjs'
import type { Cycle, Dataset, ImportFile } from '@seed/api'
import { CycleService, DatasetService, MediaService, UserService } from '@seed/api'
import { DeleteModalComponent, PageComponent } from '@seed/components'
import { ConfigService } from '@seed/services'
import { DataUploadModalComponent } from '../data-upload/data-upload-modal.component'
import { MeterDataUploadModalComponent } from '../data-upload/meter-upload-modal.component'

@Component({
  selector: 'seed-dataset',
  templateUrl: './dataset.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, PageComponent],
})
export class DatasetComponent implements OnDestroy, OnInit {
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _datasetService = inject(DatasetService)
  private _dialog = inject(MatDialog)
  private _mediaService = inject(MediaService)
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  columnDefs: ColDef[] = []
  cycles: Cycle[] = []
  cyclesMap: Record<number, string>
  dataset: Dataset
  datasetId = this._route.snapshot.params?.id as number
  datasetName$: Observable<string>
  importFiles: ImportFile[] = []
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  orgId: number

  ngOnInit(): void {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.orgId = orgId
        }),
        switchMap(() => this.getCycles()),
        switchMap(() => this.getDataset()),
      )
      .subscribe()
  }

  getCycles() {
    return this._cycleService.cycles$.pipe(
      tap((cycles) => {
        this.cycles = cycles
        this.cyclesMap = cycles.reduce((acc, c) => ({ ...acc, [c.id]: c.name }), {})
      }),
    )
  }

  getDataset() {
    return this._datasetService.get(this.orgId, this.datasetId).pipe(
      tap((dataset) => {
        this.dataset = dataset
        this.formatImportFiles(dataset)
        this.datasetName$ = of(dataset.name)
        this.setColumnDefs()
      }),
    )
  }

  formatImportFiles(dataset: Dataset) {
    const { importfiles } = dataset
    this.importFiles = importfiles.map((f) => ({ ...f, cycle_name: this.cyclesMap[f.cycle] }))
    this.importFiles.sort((a, b) => this.toTimestamp(b.created) - this.toTimestamp(a.created))
  }

  // Sort by the full timestamp (not the display string), treating missing/invalid dates as oldest
  toTimestamp(value: string): number {
    const time = value ? new Date(value).getTime() : NaN
    return Number.isNaN(time) ? 0 : time
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'id', hide: true },
      { field: 'uploaded_filename', headerName: 'File Name' },
      {
        field: 'created',
        headerName: 'Date Imported',
        valueFormatter: ({ value }: { value: string }) => (value ? new Date(value).toLocaleString() : ''),
        comparator: (a: string, b: string) => this.toTimestamp(a) - this.toTimestamp(b),
      },
      { field: 'source_type', headerName: 'Source Type' },
      { field: 'num_rows', headerName: 'Record Count' },
      { field: 'cycle_name', headerName: 'Cycle' },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionsRenderer, width: 400, suppressSizeToFit: true },
    ]
  }

  actionsRenderer({ data }: { data: ImportFile }) {
    const enableMapping = data.num_rows > 0 && Boolean(data.cached_second_to_fifth_row?.length)
    const enablePairing = data.num_rows > 0 && data.mapping_done && data.matching_done && data.cycle_name !== undefined

    const mappingSpan = `<span class="inline-flex items-center gap-1 border rounded-full bg-primary text-white h-8 mt-1 px-3 hover:bg-primary-800 ${enableMapping ? 'cursor-pointer' : 'opacity-25'}" title="Data Mapping" ${enableMapping ? 'data-action="dataMapping"' : ''}>`
    const pairingSpan = `<span class="inline-flex items-center gap-1 border rounded-full h-8 mt-1 px-3 hover:bg-primary-800 ${enablePairing ? 'cursor-pointer' : 'opacity-25'}" title="Data Pairing" ${enablePairing ? 'data-action="dataPairing"' : ''}>`

    return `
      <div class="flex gap-2 align-center">
        ${mappingSpan}
          <span class="text-sm">Data Mapping</span>
          <span class="material-icons text-secondary text-sm">open_in_new</span>
        </span>
        ${pairingSpan}
          <span class="text-sm">Data Pairing</span>
          <span class="material-icons text-secondary text-sm">open_in_new</span>
        </span>
        <span class="material-icons cursor-pointer text-secondary my-auto" title="Download Dataset" data-action="download">cloud_download</span>
        <span class="material-icons cursor-pointer text-secondary my-auto" title="Delete Dataset" data-action="delete">clear</span>
      </div>
    `
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.sizeColumnsToFit()
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'actions') return

    const target = event.event.target as HTMLElement
    const action = target.closest('[data-action]')?.getAttribute('data-action')
    const { id } = event.data as { id: number }

    const importFile = this.importFiles.find((f) => f.id === id)

    if (action === 'delete') {
      this.deleteImportFile(importFile)
    } else if (action === 'download') {
      this.downloadDocument(importFile.file, importFile.uploaded_filename)
    } else if (action === 'dataMapping') {
      void this._router.navigate(['/data/mappings/', importFile.id])
    } else if (action === 'dataPairing') {
      void this._router.navigate(['/data/pairing', importFile.id, 'properties'])
    }
  }

  deleteImportFile(importFile: ImportFile) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Import File', instance: importFile.uploaded_filename },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._datasetService.deleteFile(this.orgId, importFile.id)),
        switchMap(() => this.getDataset()),
      )
      .subscribe()
  }

  addDataFile = () => {
    if (!this.dataset || !this.cycles.length) return
    this._dialog
      .open(DataUploadModalComponent, {
        width: '40rem',
        data: { orgId: this.orgId, dataset: this.dataset, cycles: this.cycles },
      })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.getDataset()),
      )
      .subscribe()
  }

  addMeterData = () => {
    if (!this.dataset || !this.cycles.length) return
    this._dialog
      .open(MeterDataUploadModalComponent, {
        width: '60rem',
        data: { orgId: this.orgId, datasetId: this.dataset.id, cycleId: this.cycles[0].id, file: null },
      })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.getDataset()),
      )
      .subscribe()
  }

  // `file` is the import file's path on the server, which the media service maps to the media endpoint
  downloadDocument(file: string, filename: string) {
    this._mediaService.download(file, filename).subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
