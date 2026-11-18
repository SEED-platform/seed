import { CommonModule } from '@angular/common'
import type { OnChanges, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridOptions, GridReadyEvent, Theme } from 'ag-grid-community'
import { filter, type Observable, switchMap } from 'rxjs'
import { type DataLogger, SensorService } from '@seed/api'
import { DeleteModalComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { FormModalComponent } from './modal/form-modal.component'
import { SensorReadingsUploadModalComponent } from './modal/sensor-readings-upload.component'
import { SensorsUploadModalComponent } from './modal/sensors-upload.component'

@Component({
  selector: 'seed-inventory-detail-sensors-data-loggers-grid',
  templateUrl: './data-loggers-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports],
})
export class DataLoggersGridComponent implements OnChanges {
  @Input() cycleId: number
  @Input() dataLoggers: DataLogger[]
  @Input() datasetId: string
  @Input() gridTheme$: Observable<Theme>
  @Input() orgId: number
  @Input() viewId: number
  @Output() excludedIdsChange = new EventEmitter<number[]>()
  private _dialog = inject(MatDialog)
  private _sensorService = inject(SensorService)
  excludedIds: number[] = []
  gridApi: GridApi
  gridHeight = 0
  gridOptions: GridOptions = {
    rowSelection: {
      mode: 'multiRow',
      checkboxes: true,
      headerCheckbox: true,
    },
    onSelectionChanged: () => {
      this.selectionChanged()
    },
  }

  columnDefs: ColDef[] = [
    { field: 'id', hide: true },
    { field: 'actions', headerName: 'Actions', cellRenderer: this.actionRenderer, width: 300 },
    { field: 'display_name', headerName: 'Display Name' },
    { field: 'identifier', headerName: 'Data Logger ID', hide: true },
    { field: 'location_description', headerName: 'Location Description' },
    { field: 'manufacturer_name', headerName: 'Manufacturer Name' },
    { field: 'model_name', headerName: 'Model Name' },
    { field: 'serial_number', headerName: 'Serial Number' },
  ]

  ngOnChanges(changes: SimpleChanges) {
    if (changes.dataLoggers) {
      this.gridHeight = Math.min(this.dataLoggers.length * 43 + 50, 400)

      // hide column if all values are falsy
      const constantCols = new Set(['id', 'display_name', 'location_description', 'actions'])
      const showColumn = (field: string, rowData: Record<string, unknown>[]) => rowData.some((row) => !!row[field])
      this.columnDefs = this.columnDefs.filter((colDef) => constantCols.has(colDef.field) || showColumn(colDef.field, this.dataLoggers))

      // select all on grid load
      setTimeout(() => {
        if (this.gridApi && !this.gridApi.isDestroyed()) {
          this.gridApi?.selectAll()
        }
      }, 100)
    }
  }

  actionRenderer() {
    return `
      <div class="flex gap-2 align-center">
        <span class="inline-flex items-center gap-1 cursor-pointer text-secondary border rounded-full h-8 mt-1 px-3 hover:bg-blue-200 dark:hover:bg-sky-900" title="Add Sensors" data-action="addSensors">
          <span class="material-icons text-base">add</span>
          <span class="text-sm">Sensors</span>
        </span>
        <span class="inline-flex items-center gap-1 cursor-pointer text-secondary border rounded-full h-8 mt-1 px-3 hover:bg-blue-200 dark:hover:bg-sky-900"" title="Add Readings" data-action="addReadings">
          <span class="material-icons text-base">add</span>
          <span class="text-sm">Readings</span>
        </span>
        <span class="mt-2 material-icons cursor-pointer text-secondary" title="Edit" data-action="edit">edit</span>
        <span class="mt-2 material-icons cursor-pointer text-secondary" title="Delete" data-action="delete">clear</span>
      </div>
    `
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'actions') return

    const target = event.event.target as HTMLElement
    const action = target.closest('[data-action]')?.getAttribute('data-action')
    const { id } = event.data as { id: number }
    const dataLogger = this.dataLoggers.find((dl) => dl.id === id)

    if (action === 'edit') {
      this.editDataLogger(dataLogger)
    } else if (action === 'delete') {
      this.deleteDataLogger(dataLogger)
    } else if (action === 'addSensors') {
      this.addSensors(dataLogger)
    } else if (action === 'addReadings') {
      this.addReadings(dataLogger)
    }
  }

  addSensors(dataLogger: DataLogger) {
    this._dialog.open(SensorsUploadModalComponent, {
      width: '60rem',
      data: {
        dataLoggerId: dataLogger.id,
        datasetId: this.datasetId,
        cycleId: this.cycleId,
        orgId: this.orgId,
        viewId: this.viewId,
      },
    })
  }

  addReadings(dataLogger: DataLogger) {
    this._dialog.open(SensorReadingsUploadModalComponent, {
      width: '60rem',
      data: {
        dataLoggerId: dataLogger.id,
        datasetId: this.datasetId,
        cycleId: this.cycleId,
        orgId: this.orgId,
        viewId: this.viewId,
      },
    })
  }

  editDataLogger(dataLogger: DataLogger) {
    const existingDisplayNames = this.dataLoggers.filter((dl) => dl.id !== dataLogger.id).map((dl) => dl.display_name)
    this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, viewId: this.viewId, dataLogger, existingDisplayNames },
    })
  }

  deleteDataLogger(dataLogger: DataLogger) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Sensor', instance: dataLogger.display_name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._sensorService.deleteDataLogger(this.orgId, this.viewId, dataLogger.id)),
      )
      .subscribe()
  }

  selectionChanged() {
    const allIds = this.dataLoggers.map((dl: DataLogger) => dl.id)
    const selectedIds = this.gridApi.getSelectedRows().map((r: { id: number }) => r.id)
    const newExcludedIds = allIds.filter((id) => !selectedIds.includes(id))
    if (newExcludedIds.length === this.excludedIds.length) return

    this.excludedIds = newExcludedIds
    this.excludedIdsChange.emit(this.excludedIds)
  }
}
