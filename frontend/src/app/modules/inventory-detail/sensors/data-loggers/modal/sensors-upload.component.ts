import { CommonModule } from '@angular/common'
import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef } from 'ag-grid-community'
import { Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { ProgressResponse, Sensor } from '@seed/api'
import { SensorService } from '@seed/api'
import { ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { ProgressBarObj } from '@seed/services/uploader'
import { UploaderService } from '@seed/services/uploader'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-detail-sensors-upload',
  templateUrl: './sensors-upload.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, ProgressBarComponent],
})
export class SensorsUploadModalComponent implements OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper
  private _dialogRef = inject(MatDialogRef<SensorsUploadModalComponent>)
  private _configService = inject(ConfigService)
  private _uploaderService = inject(UploaderService)
  private _sensorService = inject(SensorService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  readonly allowedTypes = [
    'application/vnd.ms-excel', // .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
    'text/csv',
    'text/plain',
  ]
  file?: File
  fileId: number
  validFile = false
  completed = { 1: false, 2: false, 3: false }
  proposedImports: Sensor[] = []
  importedSensors: Sensor[] = []
  gridHeight = 0
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

  columnDefs: ColDef[] = [
    { field: 'display_name', headerName: 'Display Name' },
    { field: 'type', headerName: 'Type' },
    { field: 'location_description', headerName: 'Location Description' },
    { field: 'units', headerName: 'Units' },
    { field: 'column_name', headerName: 'Column Name' },
    { field: 'description', headerName: 'Description' },
  ]

  data = inject(MAT_DIALOG_DATA) as {
    cycleId: number;
    dataLoggerId: number;
    datasetId: string;
    orgId: number;
    viewId: number;
  }

  // select file
  step1(fileList: FileList) {
    if (fileList.length !== 1) return
    const { orgId, viewId, dataLoggerId, datasetId } = this.data
    const [file] = fileList
    this.file = file
    const sourceType = 'SensorMetadata'
    this.uploading = true

    return this._uploaderService
      .fileUpload(orgId, this.file, sourceType, datasetId)
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(({ import_file_id }) => {
          this.fileId = import_file_id
          this.completed[1] = true
        }),
        switchMap(() => this._uploaderService.sensorPreview(orgId, viewId, dataLoggerId, this.fileId)),
        tap(({ proposed_imports }) => {
          this.proposedImports = proposed_imports
          this.gridHeight = Math.min(this.proposedImports.length * 35 + 42, 300)
          this.stepper.next()
          this.validateImports()
          this.uploading = false
        }),
      )
      .subscribe()
  }

  validateImports() {
    this.validFile = this.proposedImports.every((item) => item?.column_name)
    this.completed[2] = this.validFile
    if (!this.validFile) {
      this._snackBar.alert('Invalid file format.')
    }
  }

  step3() {
    this.stepper.next()
    this.inProgress = true
    const { orgId, viewId, cycleId } = this.data

    const failureFn = () => {
      this._snackBar.alert('File Upload Failed')
    }

    const successFn = () => {
      this.completed[3] = true
      this._sensorService.listSensors(orgId, viewId)
      this._snackBar.success('Sensors uploaded successfully')
      this.importedSensors = this.progressBarObj.message as Sensor[]
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

  dismiss() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
