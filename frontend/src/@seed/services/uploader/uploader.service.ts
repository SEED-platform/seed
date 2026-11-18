import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, combineLatest, finalize, interval, of, Subject, switchMap, takeUntil, takeWhile, tap, throwError } from 'rxjs'
import type { ProgressResponse } from '@seed/api'
import { ErrorService } from '../error'
import type {
  CheckProgressLoopParams,
  ExportDataType,
  GreenButtonMeterPreview,
  MeterPreviewResponse,
  ProgressBarObj,
  SensorPreviewResponse,
  SensorReadingPreview,
  UpdateProgressBarObjParams,
  UploadResponse,
} from './uploader.types'

@Injectable({ providedIn: 'root' })
export class UploaderService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)

  get defaultProgressBarObj(): ProgressBarObj {
    return {
      message: [],
      progress: 0,
      total: 100,
      complete: false,
      statusMessage: '',
      progressLastUpdated: null,
      progressLastChecked: null,
    }
  }

  /*
   * Checks a progress key for updates until it completes
   */
  checkProgressLoop({
    progressKey,
    offset,
    multiplier,
    successFn,
    failureFn,
    progressBarObj,
    subProgress,
  }: CheckProgressLoopParams): Observable<ProgressResponse> {
    const isCompleted = (status: string) => ['error', 'success', 'warning'].includes(status)

    let progressLoop$ = interval(750).pipe(
      switchMap(() => this.checkProgress(progressKey)),
      tap((response) => {
        this._updateProgressBarObj({ data: response, offset, multiplier, progressBarObj })
        if (response.status === 'success') successFn?.(response)
      }),
      catchError(() => {
        // TODO the interval needs to continue if the error was network-related
        failureFn?.()
        return throwError(() => new Error('Progress check failed'))
      }),
    )

    // subProgress loops run until parent progress completes
    if (!subProgress) {
      progressLoop$ = progressLoop$.pipe(
        takeWhile((response) => !isCompleted(response.status), true), // end stream
      )
    }

    return progressLoop$
  }

  /*
   * Check the progress of Main Progress and its Sub Progress
   * Main progress will run until it completes
   * Sub Progresses can complete several times and will run continuously until Main Progress is completed
   * the stop$ stream is used to end the Sub Progress stream
   */
  checkProgressLoopMainSub(mainParams: CheckProgressLoopParams, subParams: CheckProgressLoopParams) {
    const stop$ = new Subject<void>()
    const main$ = this.checkProgressLoop(mainParams).pipe(
      finalize(() => {
        stop$.next()
        stop$.complete()
      }),
    )

    const sub$ = this.checkProgressLoop({ ...subParams, subProgress: true }).pipe(takeUntil(stop$))

    return combineLatest([main$, sub$])
  }

  /*
   * Fetches progress for a given progress key
   */
  checkProgress(progressKey: string): Observable<ProgressResponse> {
    const url = `/api/v3/progress/${progressKey}/`
    return this._httpClient.get<ProgressResponse>(url).pipe(
      catchError((error) => {
        console.error('Error fetching progress:', error)
        return of(null)
      }),
    )
  }

  greenButtonMetersPreview(orgId: number, viewId: number, systemId: number, fileId: number): Observable<GreenButtonMeterPreview> {
    const url = `/api/v3/import_files/${fileId}/greenbutton_meters_preview/`
    const params: Record<string, number> = { organization_id: orgId }
    if (viewId) {
      params.view_id = viewId
    } else if (systemId) {
      params.system_id = systemId
    }

    return this._httpClient.get<GreenButtonMeterPreview>(url, { params }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching greenButton preview')
      }),
    )
  }

  fileUpload(orgId: number, file: File, sourceType: string, importRecordId: string): Observable<UploadResponse> {
    const url = `/api/v3/upload/?organization_id=${orgId}`
    const formData = new FormData()
    formData.append('file', file, file.name)
    formData.append('source_type', sourceType)
    formData.append('import_record', importRecordId)

    return this._httpClient.post<UploadResponse>(url, formData).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error uploading file')
      }),
    )
  }

  sensorPreview(orgId: number, viewId: number, dataLoggerId: number, fileId: number): Observable<SensorPreviewResponse> {
    const url = `/api/v3/import_files/${fileId}/sensors_preview/`
    const params = { organization_id: orgId, view_id: viewId, data_logger_id: dataLoggerId }
    return this._httpClient.get<SensorPreviewResponse>(url, { params }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching sensor preview')
      }),
    )
  }

  sensorReadingsPreview(orgId: number, viewId: number, dataLoggerId: number, fileId: number): Observable<SensorReadingPreview[]> {
    const url = `/api/v3/import_files/${fileId}/sensor_readings_preview/`
    const params = { organization_id: orgId, view_id: viewId, data_logger_id: dataLoggerId }
    return this._httpClient.get<SensorReadingPreview[]>(url, { params }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching sensor readings preview')
      }),
    )
  }

  metersPreview(orgId: number, fileId: number): Observable<MeterPreviewResponse> {
    const url = `/api/v3/import_files/${fileId}/pm_meters_preview/?organization_id=${orgId}`
    return this._httpClient.get<MeterPreviewResponse>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching meters preview')
      }),
    )
  }

  saveRawData(orgId: number, cycleId: number, fileId: number, multipleCycleUpload = false): Observable<ProgressResponse> {
    const url = `/api/v3/import_files/${fileId}/start_save_data/?organization_id=${orgId}`
    const body = { cycle_id: cycleId, multiple_cycle_upload: multipleCycleUpload }
    return this._httpClient.post<ProgressResponse>(url, body).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error saving raw data')
      }),
    )
  }

  stringToBlob(data: string, exportType: ExportDataType) {
    const base64ToBlob = (base64: string): Blob => {
      const binary = atob(base64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i)
      }

      return new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    }

    const blobMap: Record<ExportDataType, () => Blob> = {
      csv: () => new Blob([data], { type: 'text/csv' }),
      xlsx: () => base64ToBlob(data),
      geojson: () => new Blob([JSON.stringify(data, null, '\t')], { type: 'application/geo+json' }),
    }

    return blobMap[exportType]()
  }

  /*
   * Updates the progress bar object with incoming progress data.
   */
  private _updateProgressBarObj({ data, offset, multiplier, progressBarObj }: UpdateProgressBarObjParams): void {
    const rightNow = Date.now()
    progressBarObj.progressLastChecked = rightNow

    const newProgressValue = Math.min(Math.max(data.progress * multiplier + offset, 0), 100)
    const updatingProgress = newProgressValue !== progressBarObj.progress || progressBarObj.statusMessage !== data.status_message
    if (updatingProgress) {
      progressBarObj.progressLastUpdated = rightNow
    }

    if (data.total_records) {
      progressBarObj.totalRecords = data.total_records
    }
    if (data.completed_records) {
      progressBarObj.completedRecords = data.completed_records
    }
    progressBarObj.progress = newProgressValue
    progressBarObj.statusMessage = data.status_message
    progressBarObj.message = data.message
  }
}
