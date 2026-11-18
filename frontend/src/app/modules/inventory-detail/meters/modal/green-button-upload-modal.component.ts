import { CommonModule } from '@angular/common'
import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef } from 'ag-grid-community'
import { Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { ProgressResponse } from '@seed/api'
import { MeterService } from '@seed/api'
import { ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { MeterImport, ProgressBarObj, ValidatedTypeUnit } from '@seed/services/uploader'
import { UploaderService } from '@seed/services/uploader'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-detail-green-button-upload-modal',
  templateUrl: './green-button-upload-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, FormsModule, MaterialImports, ProgressBarComponent, ReactiveFormsModule],
})
export class GreenButtonUploadModalComponent implements OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper
  private _dialogRef = inject(MatDialogRef<GreenButtonUploadModalComponent>)
  private _configService = inject(ConfigService)
  private _meterService = inject(MeterService)
  private _snackBar = inject(SnackBarService)
  private _uploaderService = inject(UploaderService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  allowedTypes = ['application/xml', 'text/xml']
  completed = { 1: false, 2: false }
  file: File
  fileId: number
  proposedImports: MeterImport[] = []
  typeUnits: ValidatedTypeUnit[] = []
  importedData: MeterImport[] = []
  gridTheme$ = this._configService.gridTheme$
  inProgress = false
  uploading = false
  progressBarObj: ProgressBarObj = {
    message: [],
    progress: 0,
    total: 100,
    complete: false,
    statusMessage: '',
    progressLastUpdated: null,
    progressLastChecked: null,
  }

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewId: number;
    cycleId: number;
    systemId: number;
    datasetId: number;
    interval: string;
    excludedIds: number[];
  }

  columnDefs: Record<string, ColDef[]> = {
    step2: [
      { field: 'source_id', headerName: 'GreenButton UsagePoint' },
      { field: 'type', headerName: 'Type' },
      { field: 'incoming', headerName: 'Incoming' },
    ],
    step2Units: [
      { field: 'parsed_type', headerName: 'Parsed Type' },
      { field: 'parsed_unit', headerName: 'Parsed Unit' },
    ],
    step4: [
      { field: 'source_id', headerName: 'GreenButton UsagePoint' },
      { field: 'type', headerName: 'Type' },
      { field: 'successfully_imported', headerName: 'Successfully Imported' },
      { field: 'incoming', headerName: 'Incoming' },
    ],
  }

  step1(fileList: FileList) {
    if (fileList.length !== 1) return
    const { datasetId, orgId, systemId, viewId } = this.data
    const [file] = fileList
    this.file = file
    const sourceType = 'GreenButton'
    this.uploading = true

    return this._uploaderService
      .fileUpload(orgId, this.file, sourceType, datasetId.toString())
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(({ import_file_id }) => {
          this.fileId = import_file_id
          this.completed[1] = true
        }),
        switchMap(() => this._uploaderService.greenButtonMetersPreview(orgId, viewId, systemId, this.fileId)),
        tap(({ proposed_imports, validated_type_units }) => {
          this.proposedImports = proposed_imports
          this.typeUnits = validated_type_units
          this.completed[2] = true
          this.stepper.next()
          this.uploading = false
        }),
      )
      .subscribe()
  }

  step3() {
    this.stepper.next()
    this.inProgress = true
    const { orgId, viewId, cycleId, interval, excludedIds } = this.data

    const failureFn = () => {
      this._snackBar.alert('File Upload Failed')
    }

    const successFn = () => {
      this.completed[3] = true
      this._meterService.list(orgId, viewId)
      this._meterService.listReadings(orgId, viewId, interval, excludedIds)
      this._snackBar.success('Meter data uploaded successfully')
      this.importedData = this.progressBarObj.message as MeterImport[]
      setTimeout(() => {
        this.stepper.next()
      })
    }

    this._uploaderService
      .saveRawData(orgId, cycleId, this.fileId)
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((response: ProgressResponse) => {
          this.progressBarObj.progress = response.progress
        }),
        switchMap((data) => {
          return this._uploaderService.checkProgressLoop({
            progressKey: data.progress_key,
            successFn,
            failureFn,
            progressBarObj: this.progressBarObj,
          })
        }),
      )
      .subscribe()
  }

  gridHeight(data: unknown[]) {
    return Math.min(data.length * 43 + 50, 300)
  }

  dismiss() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
