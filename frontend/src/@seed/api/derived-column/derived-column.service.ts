import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { catchError, map, type Observable, ReplaySubject, switchMap, tap } from 'rxjs'
import { ErrorService } from '@seed/services/error/error.service'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { OrganizationService } from '../organization'
import type { DerivedColumn, DerivedColumnResponse, DerivedColumnsResponse } from './derived-column.types'

@Injectable({ providedIn: 'root' })
export class DerivedColumnService {
  private _httpClient = inject(HttpClient)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)
  private _errorService = inject(ErrorService)
  private _derivedColumns = new ReplaySubject<DerivedColumn[]>()

  orgId: number

  derivedColumns$ = this._derivedColumns.asObservable()

  constructor() {
    this._organizationService.currentOrganization$.pipe(switchMap(({ org_id }) => this.get(org_id))).subscribe()
  }

  get(orgId: number): Observable<DerivedColumn[]> {
    // exclude param inventory_type to return a mixed array of property and taxlot derived columns
    // and let component filter as inventory type can get lost
    const url = `/api/v3/derived_columns/?organization_id=${orgId}`
    return this._httpClient.get<DerivedColumnsResponse>(url).pipe(
      map(({ derived_columns }) => derived_columns),
      tap((derived_columns) => {
        this._derivedColumns.next(derived_columns)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching derived columns')
      }),
    )
  }

  post({ orgId, data }) {
    const url = `/api/v3/derived_columns/?organization_id=${orgId}`
    return this._httpClient.post<DerivedColumnResponse>(url, data).pipe(
      tap(({ derived_column }) => {
        this._snackBar.success(`Derived column ${derived_column.name} created`)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating derived column')
      }),
    )
  }

  put({ orgId, id, data }) {
    const url = `/api/v3/derived_columns/${id}/?organization_id=${orgId}`
    return this._httpClient.put<DerivedColumnResponse>(url, data).pipe(
      tap(({ derived_column }) => {
        this._snackBar.success(`Derived column ${derived_column.name} updated`)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating derived column')
      }),
    )
  }

  delete({ orgId, id }) {
    const url = `/api/v3/derived_columns/${id}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Derived column deleted')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting derived column')
      }),
    )
  }
}
