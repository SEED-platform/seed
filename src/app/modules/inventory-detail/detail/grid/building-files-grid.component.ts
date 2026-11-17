import { CommonModule } from '@angular/common'
import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import { map } from 'rxjs'
import { MediaService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType, ViewResponse } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-building-files-grid',
  templateUrl: './building-files-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports],
})
export class BuildingFilesGridComponent implements OnInit {
  @Input() view: ViewResponse
  @Input() type: InventoryType
  private _configService = inject(ConfigService)
  private _mediaService = inject(MediaService)
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$.pipe(map((t) => t.withParams({ oddRowBackgroundColor: 'rgba(0,0,0,0.04)' })))
  columnDefs: ColDef[] = []
  rowData: Record<string, unknown>[] = []
  defaultColDef = {
    sortable: false,
    filter: false,
    resizable: true,
    suppressMovable: true,
  }

  ngOnInit(): void {
    this.setBuildingFilesGrid()
  }

  setBuildingFilesGrid() {
    this.setColumnDefs()
    this.setRowData()
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'file_type', headerName: 'File Type' },
      { field: 'filename', headerName: 'File Name' },
      { field: 'created', headerName: 'Created' },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionRenderer },
    ]
  }

  actionRenderer = () => {
    return `
      <div class="flex gap-2 mt-2 align-center">
        <span class="material-icons cursor-pointer text-secondary" data-action="download">cloud_download</span>
      </div>
    `
  }

  setRowData() {
    const files = this.view.state.files
    for (const { created, file, file_type, filename } of files) {
      this.rowData.push({ created, file, file_type, filename })
    }
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'actions') return
    this.downloadDocument(event.data)
  }

  downloadDocument(data: unknown) {
    const { file, filename } = data as { file: string; filename: string }
    this._mediaService.download(file, filename).subscribe()
  }

  get gridHeight() {
    return Math.min(this.rowData.length * 42 + 50, 500)
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi = params.api
    this.gridApi.sizeColumnsToFit()
  }
}
