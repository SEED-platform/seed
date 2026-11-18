import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { RouterModule } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef } from 'ag-grid-community'
import { Subject, take, takeUntil, tap } from 'rxjs'
import type { MatchingResultsResponse } from '@seed/api'
import { DatasetService, MappingService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { UploaderService } from '@seed/services/uploader'
import type { InventoryType } from 'app/modules/inventory'
import { MeterDataUploadModalComponent } from '../../data-upload/meter-upload-modal.component'

@Component({
  selector: 'seed-match-merge-results',
  templateUrl: './results.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, RouterModule],
})
export class ResultsComponent implements OnChanges, OnDestroy {
  @Input() cycleId: number
  @Input() datasetId: number
  @Input() inventoryType: InventoryType
  @Input() importFileId: number
  @Input() inProgress = true
  @Input() orgId: number

  private _configService = inject(ConfigService)
  private _datasetService = inject(DatasetService)
  private _dialog = inject(MatDialog)
  private _mappingService = inject(MappingService)
  private _uploaderService = inject(UploaderService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  gridTheme$ = this._configService.gridTheme$
  generalData: Record<string, unknown>[]
  generalColDefs: ColDef[] = []
  inventoryColDefs: ColDef[] = [
    { field: 'status', headerName: 'Status' },
    { field: 'count', headerName: 'Count' },
  ]
  matchingResults: MatchingResultsResponse
  propertyData: Record<string, unknown>[] = []
  taxlotData: Record<string, unknown>[] = []
  hasPropertyData = false
  hasTaxlotData = false
  checkingMeterTab = true
  showMeterButton = true

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.inProgress.currentValue === false) {
      this.getMatchingResults()
    }
  }

  getMatchingResults() {
    this._mappingService
      .getMatchingResults(this.orgId, this.importFileId)
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((results) => {
          this.setGrid(results)
        }),
      )
      .subscribe()

    this._datasetService
      .checkMetersTabExists(this.orgId, this.importFileId)
      .pipe(
        take(1),
        tap((hasData) => {
          this.checkingMeterTab = false
          this.showMeterButton = hasData
        }),
      )
      .subscribe()
  }

  setGrid(results: MatchingResultsResponse) {
    this.matchingResults = results
    this.setInventoryGrids()
  }

  setInventoryGrids() {
    this.setPropertyData()
    this.setTaxLotData()
  }

  setPropertyData() {
    const { properties } = this.matchingResults
    this.hasPropertyData = Object.values(properties).some((v) => v)
    this.propertyData = Object.entries(properties)
      .filter(([_, v]) => v)
      .map(([k, v]) => ({
        status: this.readableString(k),
        count: v,
      }))
  }

  setTaxLotData() {
    const { tax_lots } = this.matchingResults
    this.hasTaxlotData = Object.values(tax_lots).some((v) => v)
    this.taxlotData = Object.entries(tax_lots)
      .filter(([_, v]) => v)
      .map(([k, v]) => ({
        status: this.readableString(k),
        count: v,
      }))
  }

  readableString(str: string) {
    return str.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
  }

  importMeters() {
    this._dialog.open(MeterDataUploadModalComponent, {
      width: '60rem',
      data: { orgId: this.orgId, datasetId: this.datasetId, cycleId: this.cycleId, reusedImportFileId: this.importFileId },
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
