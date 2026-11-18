import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { catchError, EMPTY, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { ProgressResponse } from '@seed/api'
import { CacheService, InventoryService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryExportData, InventoryType } from '../inventory.types'

@Component({
  selector: 'seed-export-modal',
  templateUrl: './export-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ModalHeaderComponent, ProgressBarComponent, ReactiveFormsModule],
})
export class ExportModalComponent implements OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper
  private _cacheService = inject(CacheService)
  private _dialogRef = inject(MatDialogRef<ExportModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _snackBar = inject(SnackBarService)
  private _uploaderService = inject(UploaderService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  progressBarObj = this._uploaderService.defaultProgressBarObj
  filename: string
  exportData: InventoryExportData

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    type: InventoryType;
    viewIds: number[];
    profileId: number;
  }

  form = new FormGroup({
    export_type: new FormControl<'csv' | 'xlsx' | 'geojson'>('csv', Validators.required),
    include_notes: new FormControl(false),
    include_meter_readings: new FormControl(false),
    name: new FormControl<string>(null, Validators.required),
  })

  export() {
    const successFn = ({ unique_id }: ProgressResponse) => {
      this._cacheService
        .getCacheEntry(this.data.orgId, unique_id)
        .pipe(
          tap((response: { data: string }) => {
            const blob = this.getBlob(response.data)
            this.downloadData(blob)
            this.close()
          }),
          take(1),
        )
        .subscribe()
    }

    this.initExport()
    this._inventoryService
      .startInventoryExport(this.data.orgId, this.exportData)
      .pipe(
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn,
            failureFn: () => {
              this.close()
            },
            progressBarObj: this.progressBarObj,
          }),
        ),
        takeUntil(this._unsubscribeAll$),
        catchError(() => {
          return EMPTY
        }),
      )
      .subscribe()
  }

  initExport() {
    this.stepper.next()
    this.formatFilename()
    this.formatExportData(this.filename)
  }

  getBlob(data: string): Blob {
    const exportType = this.form.value.export_type
    return this._uploaderService.stringToBlob(data, exportType)
  }

  downloadData(data: Blob) {
    const a = document.createElement('a')
    const url = URL.createObjectURL(data)
    a.href = url
    a.download = this.exportData.filename
    a.click()
    URL.revokeObjectURL(url)
    this._snackBar.success(`Exported ${this.exportData.filename}`)
  }

  formatFilename() {
    this.filename = this.form.value.name
    const ext = `.${this.form.value.export_type}`
    if (!this.filename.endsWith(ext)) {
      this.filename += ext
    }
  }

  formatExportData(filename: string) {
    this.exportData = {
      export_type: this.form.value.export_type,
      filename,
      ids: this.data.viewIds,
      include_meter_readings: this.form.value.include_meter_readings,
      include_notes: this.form.value.include_notes,
      profile_id: this.data.profileId,
    }
  }

  close() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
