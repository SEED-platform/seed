import { HttpClient } from '@angular/common/http'
import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { catchError, of, switchMap, tap } from 'rxjs'
import { GroupsService, OrganizationService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

export type UploadReadingsDialogData = {
  orgId: number;
  groupId: number;
  meter: {
    id: number;
    alias: string;
    type: string;
  };
}

@Component({
  selector: 'seed-upload-readings-dialog',
  templateUrl: './upload-readings-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class UploadReadingsDialogComponent implements OnInit {
  private _data = inject(MAT_DIALOG_DATA) as UploadReadingsDialogData
  private _dialogRef = inject(MatDialogRef<UploadReadingsDialogComponent>)
  private _groupsService = inject(GroupsService)
  private _organizationService = inject(OrganizationService)
  private _httpClient = inject(HttpClient)
  private _snackBar = inject(SnackBarService)

  meterName = this._data.meter.alias || `${this._data.meter.type} (ID: ${this._data.meter.id})`
  state: 'upload' | 'processing' | 'confirmation' = 'upload'
  confirmationMessage = ''
  selectedFile: File | null = null
  invalidExtension = false
  uploadSucceeded = false
  orgId: number

  ngOnInit() {
    this.orgId = this._data.orgId
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'csv' && ext !== 'xlsx') {
      this.invalidExtension = true
      this.selectedFile = null
      return
    }

    this.invalidExtension = false
    this.selectedFile = file
  }

  upload() {
    if (!this.selectedFile) return
    this.state = 'processing'
    this.uploadSucceeded = false

    const datasetName = `Meter Readings Upload - ${new Date().toISOString()}`

    // Step 1: Create dataset
    this._httpClient
      .post<{ id: number }>(`/api/v3/datasets/?organization_id=${this.orgId}`, { name: datasetName })
      .pipe(
        // Step 2: Upload file
        switchMap((dataset) => {
          const formData = new FormData()
          formData.append('file', this.selectedFile)
          formData.append('import_record', dataset.id.toString())
          formData.append('source_type', 'Meter Data')
          return this._httpClient.post<{ import_file_id: number }>(`/api/v3/upload/?organization_id=${this.orgId}`, formData)
        }),
        // Step 3: Process meter readings
        switchMap((uploadResult) => {
          return this._groupsService.uploadMeterReadings(this.orgId, uploadResult.import_file_id, this._data.meter.id)
        }),
        tap(() => {
          this.uploadSucceeded = true
        }),
        catchError((error: { error?: { message?: string }; message?: string }) => {
          this.uploadSucceeded = false
          const message = error?.error?.message || error?.message || 'Upload failed'
          return of({ message: `Failure: ${message}` })
        }),
      )
      .subscribe((result) => {
        this.state = 'confirmation'
        this.confirmationMessage = result.message
      })
  }

  dismiss() {
    this._dialogRef.close(this.uploadSucceeded)
  }
}
