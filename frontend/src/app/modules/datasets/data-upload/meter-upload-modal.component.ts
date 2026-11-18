import { CommonModule } from '@angular/common'
import type { AfterViewInit, OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef } from 'ag-grid-community'
import { catchError, EMPTY, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import { DatasetService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { UploaderService } from '@seed/services/uploader/uploader.service'
import type { MeterImport, ProgressBarObj, ValidatedTypeUnit } from '@seed/services/uploader/uploader.types'
import { csvDownload } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-meter-data-upload-modal',
  templateUrl: './meter-upload-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class MeterDataUploadModalComponent implements AfterViewInit, OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper

  private _datasetService = inject(DatasetService)
  private _dialogRef = inject(MatDialogRef<MeterDataUploadModalComponent>)
  private _configService = inject(ConfigService)
  private _uploaderService = inject(UploaderService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  readonly allowedTypes = [
    'application/vnd.ms-excel', // .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
    'text/csv',
    'text/plain',
  ]
  file?: File
  importFileId: number
  cycleId: number
  completed = { 1: false, 2: false, 3: false }
  defaultFileName = 'No file selected'
  inProgress = false
  readingGridTitle: string
  uploading = false
  gridTheme$ = this._configService.gridTheme$
  progressBarObj: ProgressBarObj = this._uploaderService.defaultProgressBarObj
  proposedImports: MeterImport[] = []
  readingHeight = 0
  importedMeters: MeterImport[] = []
  step1ProgressTitle = 'Uploading file...'
  unitHeight = 0
  validatedTypeUnits: ValidatedTypeUnit[] = []
  validFile = false
  readingDefs: ColDef[] = [
    { field: 'pm_property_id', headerName: 'PM Property ID' },
    { field: 'cycles', headerName: 'Cycles' },
    { field: 'source_id', headerName: 'PM Meter ID' },
    { field: 'type', headerName: 'Type' },
    { field: 'incoming', headerName: 'Incoming' },
  ]
  importedDefs: ColDef[] = [
    ...this.readingDefs,
    { field: 'successfully_imported', headerName: 'Successfully Imported' },
    { field: 'errors', headerName: 'Errors' },
  ]
  unitDefs: ColDef[] = [
    { field: 'parsed_type', headerName: 'Type', flex: 1 },
    { field: 'parsed_unit', headerName: 'Unit', flex: 1 },
  ]

  data = inject(MAT_DIALOG_DATA) as { datasetId: string; orgId: number; cycleId: number; reusedImportFileId: number }

  ngAfterViewInit(): void {
    // if a file is passed from the inventory upload stepper, start upload immediately
    if (this.data.reusedImportFileId) {
      this.defaultFileName = 'Reusing inventory file'
      this.reuseInventoryFileForMeters()
    }
  }

  reuseInventoryFileForMeters() {
    this.uploading = true
    this.completed[1] = true
    this.step1ProgressTitle = 'Analyzing file...'

    this._datasetService
      .reuseInventoryFileForMeters(this.data.orgId, this.data.reusedImportFileId)
      .pipe(
        take(1),
        tap((importFileId) => (this.importFileId = importFileId)),
        switchMap(() => this.getMetersPreview()),
      )
      .subscribe()
  }

  step1(fileList: FileList) {
    if (fileList.length !== 1) return
    const { orgId, datasetId } = this.data
    const [file] = fileList
    this.file = file
    const sourceType = 'PM Meter Usage'
    this.uploading = true

    return this._uploaderService
      .fileUpload(orgId, this.file, sourceType, datasetId)
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(({ import_file_id }) => {
          this.importFileId = import_file_id
          this.completed[1] = true
          this.step1ProgressTitle = 'Analyzing file...'
        }),
        switchMap(() => this.getMetersPreview()),
      )
      .subscribe()
  }

  getMetersPreview() {
    const { orgId } = this.data
    return this._uploaderService.metersPreview(orgId, this.importFileId).pipe(
      tap((response) => {
        const { proposed_imports, validated_type_units } = response
        this.setReadingTitle(proposed_imports)
        this.proposedImports = proposed_imports
        this.validatedTypeUnits = validated_type_units
        this.readingHeight = Math.min(this.proposedImports.length * 35 + 42, 250)
        this.unitHeight = Math.min(this.validatedTypeUnits.length * 35 + 42, 200)
        this.stepper.next()
        this.completed[2] = true
        this.uploading = false
      }),
      catchError(() => {
        this.uploading = false
        return EMPTY
      }),
    )
  }

  step3() {
    this.stepper.next()
    this.inProgress = true
    const { orgId, cycleId } = this.data

    const successFn = () => {
      this.completed[3] = true
      this.importedMeters = this.progressBarObj.message as MeterImport[]
      this.setReadingTitle(this.importedMeters)
      setTimeout(() => {
        this._snackBar.success('Meter Upload Complete')
        this.stepper.next()
      })
    }

    const failureFn = () => (this.inProgress = false)

    this._uploaderService
      .saveRawData(orgId, cycleId, this.importFileId)
      .pipe(
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn,
            failureFn,
            progressBarObj: this.progressBarObj,
          }),
        ),
        catchError(() => {
          this.completed[3] = true
          setTimeout(() => {
            this._snackBar.alert('Error Uploading Meters')
            this.stepper.next()
          })
          return EMPTY
        }),
      )
      .subscribe()
  }

  setReadingTitle(meterImports: MeterImport[]) {
    const meterCount = meterImports.length
    const propertyCount = new Set(meterImports.map((m) => m.pm_property_id)).size
    this.readingGridTitle = `${meterCount > 1 ? `${meterCount} Meters` : '1 Meter'} from ${propertyCount > 1 ? `${propertyCount} Properties` : '1 Property'}`
  }

  csvDownload(title: 'proposed_meter_imports' | 'validated_type_units' | 'imported_meters') {
    const data = {
      proposed_meter_imports: this.proposedImports,
      validated_type_units: this.validatedTypeUnits,
      imported_meters: this.importedMeters,
    }
    csvDownload(title, data[title])
  }

  createFileList(file: File) {
    const dt = new DataTransfer()
    dt.items.add(file)
    const fileList = dt.files
    return fileList
  }

  ngOnDestroy() {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  close = () => {
    this._dialogRef.close()
  }
}
