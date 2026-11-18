import type { HttpErrorResponse } from '@angular/common/http'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { catchError, EMPTY, forkJoin, Subject, switchMap, tap } from 'rxjs'
import { GeocodeService } from '@seed/api'
import type { ConfidenceSummary, GeocodingColumns, InventoryConfidenceSummary } from '@seed/api/geocode/geocode.types'
import { AlertComponent, ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-geocode-modal',
  templateUrl: './geocode-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, MaterialImports, ModalHeaderComponent, ProgressBarComponent, SharedImports],
})
export class GeocodeModalComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<GeocodeModalComponent>)
  private _geocodeService = inject(GeocodeService)
  private _unsubscribeAll$ = new Subject<void>()

  confidenceSummary: ConfidenceSummary = {}
  errorMessage: string
  geocodingEnabled = true
  geoColumns: GeocodingColumns = {
    PropertyState: [],
    TaxLotState: [],
  }
  hasApiKey = true
  hasEnoughGeoCols = true
  hasGeoColumns = true
  notGeocoded = false
  pMessages: boolean
  pNotGeocoded: boolean
  pSummary: InventoryConfidenceSummary
  suggestVerify = true
  tMessages: boolean
  tNotGeocoded: boolean
  tSummary: InventoryConfidenceSummary

  geocodeState: 'verify' | 'geocoding' | 'result' | 'fail' = 'verify'

  typeMap = {
    verify: 'warning',
    geocode: 'primary',
    result: 'success',
    fail: 'warn',
  }

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    type: InventoryType;
  }

  get valid() {
    return this.geocodeState === 'verify' && this.hasApiKey && this.geocodingEnabled && this.hasGeoColumns
  }

  ngOnInit(): void {
    this.getGeocodeConfig()
  }

  getGeocodeConfig() {
    forkJoin([
      this._geocodeService.checkApiKey(this.data.orgId),
      this._geocodeService.geocodingEnabled(this.data.orgId),
      this._geocodeService.geocodingColumns(this.data.orgId),
      this._geocodeService.confidenceSummary(this.data.orgId, this.data.viewIds, this.data.type),
    ])
      .pipe(
        tap(([hasApiKey, geocodingEnabled, geoColumns, confidenceSummary]) => {
          this.hasApiKey = hasApiKey
          this.geocodingEnabled = geocodingEnabled
          this.processGeoColumns(geoColumns)
          this.processConfidenceSummary(confidenceSummary)
          this.suggestVerify = hasApiKey && this.hasGeoColumns && this.geocodeState === 'verify'
        }),
      )
      .subscribe()
  }

  processGeoColumns({ PropertyState, TaxLotState }: GeocodingColumns) {
    this.hasGeoColumns = this.data.type === 'taxlots' ? TaxLotState.length > 0 : PropertyState.length > 0
  }

  processConfidenceSummary(confidenceSummary: ConfidenceSummary) {
    const { properties, taxlots } = confidenceSummary
    this.pSummary = properties
    this.tSummary = taxlots

    this.pMessages
      = !!properties
        && !!(properties.high_confidence || properties.low_confidence || properties.manual || properties.missing_address_components)
    this.tMessages
      = !!taxlots && !!(taxlots.high_confidence || taxlots.low_confidence || taxlots.manual || taxlots.missing_address_components)
  }

  close(success = false) {
    this._dialogRef.close(success)
  }

  geocodeBuildings() {
    this.geocodeState = 'geocoding'
    this.processGeoColumns({ PropertyState: [], TaxLotState: [] }) // reset columns
    this.processConfidenceSummary({}) // reset confidence summary

    const { orgId, viewIds, type } = this.data
    this._geocodeService
      .geocode(orgId, viewIds, type)
      .pipe(
        switchMap(() => this._geocodeService.confidenceSummary(this.data.orgId, this.data.viewIds, this.data.type)),
        tap((confidenceSummary) => {
          this.processConfidenceSummary(confidenceSummary)
          this.geocodeState = 'result'
        }),
        catchError((error: HttpErrorResponse) => {
          const defaultMessage = 'An error occurred while geocoding.'
          this.geocodeState = 'fail'
          this.errorMessage = error.message ?? defaultMessage
          return EMPTY
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
