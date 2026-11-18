import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef } from 'ag-grid-community'
import { Subject, switchMap, take, tap } from 'rxjs'
import type { Column, Cycle, ImportFile, MappingResultsResponse, Organization } from '@seed/api'
import { DataQualityService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { UploaderService } from '@seed/services/uploader'
import { DQCResultsModalComponent } from 'app/modules/data-quality'
import type { InventoryType } from 'app/modules/inventory'

@Component({
  selector: 'seed-save-mappings',
  templateUrl: './save-mappings.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports],
})
export class SaveMappingsComponent implements OnChanges, OnDestroy {
  @Input() columns: Column[]
  @Input() cycle: Cycle
  @Input() importFile: ImportFile
  @Input() mappingResultsResponse: MappingResultsResponse
  @Input() org: Organization
  @Input() orgId: number
  @Output() completed = new EventEmitter<null>()
  @Output() backToMapping = new EventEmitter<null>()

  private _configService = inject(ConfigService)
  private _dataQualityService = inject(DataQualityService)
  private _dialog = inject(MatDialog)
  private _uploaderService = inject(UploaderService)
  private _unsubscribeAll$ = new Subject<void>()
  propertyDefs: ColDef[] = []
  taxlotDefs: ColDef[] = []
  rowData: Record<string, unknown>[] = []
  gridTheme$ = this._configService.gridTheme$
  propertyResults: Record<string, unknown>[] = []
  taxlotResults: Record<string, unknown>[] = []
  dqcComplete = false
  dqcId: number
  inventoryType: InventoryType
  loading = true

  progressBarObj = this._uploaderService.defaultProgressBarObj

  ngOnChanges(changes: SimpleChanges): void {
    if (!changes.mappingResultsResponse?.currentValue) return

    this.loading = false
    this.propertyResults = this.mappingResultsResponse.properties
    this.taxlotResults = this.mappingResultsResponse.tax_lots

    this.startDQC()
    this.setGrid()
  }

  startDQC() {
    const successFn = () => {
      this.dqcComplete = true
    }

    this._dataQualityService
      .startDataQualityCheckForImportFile(this.orgId, this.importFile.id)
      .pipe(
        take(1),
        switchMap(({ progress_key }) => {
          return this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn,
            progressBarObj: this.progressBarObj,
          })
        }),
        tap(({ unique_id }) => {
          // data quality run IDs are integers (other tasks' IDs can be strings)
          this.dqcId = Number(unique_id)
        }),
      )
      .subscribe()
  }

  setGrid() {
    if (this.propertyResults.length) {
      const propertyKeys = Object.keys(this.propertyResults[0] ?? {})
      this.propertyDefs = this.setColumnDefs(propertyKeys)
    }
    if (this.taxlotResults.length) {
      const taxlotKeys = Object.keys(this.taxlotResults[0] ?? {})
      this.taxlotDefs = this.setColumnDefs(taxlotKeys)
    }
  }

  setColumnDefs(keys: string[]): ColDef[] {
    const aliClass = 'bg-primary bg-opacity-25'

    // remove ALI & hidden cols
    const excludeKeys = ['id', 'lot_number', 'raw_access_level_instance_error', ...this.org.access_level_names]
    keys = keys.filter((k) => !excludeKeys.includes(k))

    const hiddenColumnDefs = [
      { field: 'id', hide: true },
      { field: 'lot_number', hide: true },
    ]

    // ALI columns
    const aliErrorDef = { field: 'raw_access_level_instance_error', headerName: 'Access Level Error', cellClass: aliClass }
    let aliColumnDefs = this.org.access_level_names.map((name) => ({ field: name, cellClass: aliClass }))
    aliColumnDefs = [aliErrorDef, ...aliColumnDefs]

    // Inventory Columns
    const columnNameMap: Record<string, string> = this.columns.reduce(
      (acc, { name, display_name }) => ({ ...acc, [name]: display_name }),
      {},
    )
    const inventoryColumnDefs = keys.map((key) => ({ field: key, headerName: columnNameMap[key] || key }))

    const columnDefs = [...hiddenColumnDefs, ...aliColumnDefs, ...inventoryColumnDefs]
    return columnDefs
  }

  saveData() {
    this.completed.emit()
  }

  showDataQualityResults() {
    this._dialog.open(DQCResultsModalComponent, {
      width: '50rem',
      data: { orgId: this.orgId, dqcId: this.dqcId },
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
