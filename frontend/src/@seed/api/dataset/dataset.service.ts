import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type { CountDatasetsResponse, Dataset, DatasetResponse, ImportFile, ImportFileResponse, ListDatasetsResponse } from './dataset.types'

@Injectable({ providedIn: 'root' })
export class DatasetService {
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)
  private _datasetCount = new ReplaySubject<number>(1)
  private _datasets = new ReplaySubject<Dataset[]>(1)
  datasetCount$ = this._datasetCount.asObservable()
  datasets$ = this._datasets.asObservable()
  orgId: number

  constructor() {
    // Refresh dataset count only when the organization ID changes
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.orgId = orgId
          this.list(this.orgId)
          this.countDatasets(this.orgId)
        }),
      )
      .subscribe()
  }

  list(organizationId: number) {
    const url = `/api/v3/datasets/?organization_id=${organizationId}`
    this._httpClient
      .get<ListDatasetsResponse>(url)
      .pipe(
        map(({ datasets }) => datasets),
        tap((datasets) => {
          this._datasets.next(datasets)
        }),
      )
      .subscribe()
  }

  get(orgId: number, datasetId: number): Observable<Dataset> {
    const url = `/api/v3/datasets/${datasetId}/?organization_id=${orgId}`
    return this._httpClient.get<DatasetResponse>(url).pipe(
      map(({ dataset }) => dataset),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching dataset')
      }),
    )
  }

  create(orgId: number, name: string): Observable<Dataset> {
    const url = `/api/v3/datasets/?organization_id=${orgId}`
    return this._httpClient.post<Dataset>(url, { name }).pipe(
      tap((response) => {
        console.log('temp', response)
      }),
      tap(() => {
        this.countDatasets(orgId)
        this.list(orgId)
        // this._snackBar.success('Dataset created successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating dataset count')
      }),
    )
  }

  update(orgId: number, datasetId: number, name: string): Observable<Dataset> {
    const url = `/api/v3/datasets/${datasetId}/?organization_id=${orgId}`
    return this._httpClient.put<Dataset>(url, { dataset: name }).pipe(
      tap((response) => {
        console.log('temp', response)
      }),
      tap(() => {
        this.countDatasets(orgId)
        this.list(orgId)
        this._snackBar.success('Dataset updated successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating dataset')
      }),
    )
  }

  delete(orgId: number, datasetId: number) {
    const url = `/api/v3/datasets/${datasetId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this.countDatasets(orgId)
        this.list(orgId)
        this._snackBar.success('Dataset deleted successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting dataset')
      }),
    )
  }

  countDatasets(orgId: number) {
    this._httpClient
      .get<CountDatasetsResponse>(`/api/v3/datasets/count/?organization_id=${orgId}`)
      .pipe(
        map(({ datasets_count }) => datasets_count),
        tap((datasetsCount) => {
          this._datasetCount.next(datasetsCount)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching dataset count')
        }),
      )
      .subscribe()
  }

  deleteFile(orgId: number, fileId: number) {
    const url = `/api/v3/import_files/${fileId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('File deleted successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting file')
      }),
    )
  }

  getImportFile(orgId: number, fieldId: number): Observable<ImportFile> {
    const url = `/api/v3/import_files/${fieldId}/?organization_id=${orgId}`
    return this._httpClient.get<ImportFileResponse>(url).pipe(
      map(({ import_file }) => import_file),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching import file')
      }),
    )
  }

  checkMetersTabExists(orgId: number, fileId: number): Observable<boolean> {
    const url = `/api/v3/import_files/${fileId}/check_meters_tab_exists?organization_id=${orgId}`
    return this._httpClient.get<{ status: string; data: boolean }>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error checking meters tab existence')
      }),
    )
  }

  reuseInventoryFileForMeters(orgId: number, fileId: number): Observable<number> {
    const url = '/api/v3/import_files/reuse_inventory_file_for_meters/'
    const data = { organization_id: orgId, import_file_id: fileId }
    return this._httpClient.post<{ import_file_id: number }>(url, data).pipe(
      map(({ import_file_id }) => import_file_id),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error reusing file for meter data')
      }),
    )
  }
}
