import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef } from 'ag-grid-community'
import { catchError, EMPTY, filter, Subject, switchMap, take, tap } from 'rxjs'
import { UbidService } from '@seed/api'
import { AlertComponent, ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType } from 'app/modules/inventory'

@Component({
  selector: 'seed-ubid-decode-modal',
  templateUrl: './ubid-decode.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AlertComponent, CommonModule, MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class UbidDecodeComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<UbidDecodeComponent>)
  private _unsubscribeAll$ = new Subject<void>()
  private _ubidService = inject(UbidService)
  private _configService = inject(ConfigService)

  colDefs: ColDef[] = [
    { field: 'key', flex: 1 },
    { field: 'value', flex: 0.5 },
  ]
  errorMessage: string
  gridHeight = 175
  gridTheme$ = this._configService.gridTheme$
  rowData: { key: string; value: number }[]
  status: 'review' | 'complete' | 'inProgress' | 'error' = 'inProgress'

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    type: InventoryType;
  }

  ngOnInit(): void {
    this._ubidService
      .decodeResults(this.data.orgId, this.data.viewIds, this.data.type)
      .pipe(
        take(1),
        tap((results) => {
          this.rowData = [
            { key: 'UBID Not Yet Decoded', value: results.ubid_not_decoded },
            { key: 'UBID Already Decoded - unlikely to change', value: results.ubid_successfully_decoded },
            { key: 'Missing UBID - will be ignored', value: results.ubid_unpopulated },
          ]
          this.status = 'review'
        }),
      )
      .subscribe()
  }

  onSubmit() {
    this.status = 'inProgress'
    this._ubidService
      .decodeByIds(this.data.orgId, this.data.viewIds, this.data.type)
      .pipe(
        filter(({ status }) => status === 'success'),
        switchMap(() => this._ubidService.decodeResults(this.data.orgId, this.data.viewIds, this.data.type)),
        take(1),
        tap((results) => {
          this.gridHeight = 135
          this.rowData = [
            { key: 'UBID Not Decoded', value: results.ubid_not_decoded },
            { key: 'UBID Successfully Decoded', value: results.ubid_successfully_decoded },
          ]
          this.status = 'complete'
        }),
        catchError(() => {
          this.status = 'error'
          this.errorMessage = 'An error occurred while decoding UBIDs.'
          return EMPTY
        }),
      )
      .subscribe()
  }

  close(success = false): void {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
