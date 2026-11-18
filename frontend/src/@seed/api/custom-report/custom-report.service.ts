import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { UserService } from '../user'
import type {
  CustomReport,
  CustomReportEvaluateResponse,
  CustomReportResponse,
  CustomReportsResponse,
  CustomReportUpsertPayload,
} from './custom-report.types'

@Injectable({ providedIn: 'root' })
export class CustomReportService {
  private _errorService = inject(ErrorService)
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)

  private _customReports = new ReplaySubject<CustomReport[]>(1)
  private _currentReports: CustomReport[] = []
  customReports$ = this._customReports.asObservable()

  constructor() {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.list(orgId)
        }),
      )
      .subscribe()
  }

  list(orgId: number) {
    const url = `/api/v3/data_views/?organization_id=${orgId}`
    this._httpClient
      .get<CustomReportsResponse>(url)
      .pipe(
        take(1),
        map(({ data_views }) => {
          this._currentReports = data_views
          this._customReports.next(data_views)
          return data_views
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching custom reports')
        }),
      )
      .subscribe()
  }

  get(orgId: number, id: number): Observable<CustomReport> {
    const url = `/api/v3/data_views/${id}/?organization_id=${orgId}`
    return this._httpClient.get<CustomReportResponse>(url).pipe(
      map(({ data_view }) => data_view),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching custom report')
      }),
    )
  }

  create(orgId: number, payload: CustomReportUpsertPayload): Observable<CustomReportResponse> {
    const url = `/api/v3/data_views/?organization_id=${orgId}`
    return this._httpClient.post<CustomReportResponse>(url, payload).pipe(
      tap(({ data_view }) => {
        this._currentReports = [...this._currentReports, data_view]
        this._customReports.next(this._currentReports)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating custom report')
      }),
    )
  }

  update(orgId: number, id: number, payload: CustomReportUpsertPayload): Observable<CustomReportResponse> {
    const url = `/api/v3/data_views/${id}/?organization_id=${orgId}`
    return this._httpClient.put<CustomReportResponse>(url, payload).pipe(
      tap(({ data_view }) => {
        this._currentReports = this._currentReports.map((r) => (r.id === id ? data_view : r))
        this._customReports.next(this._currentReports)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating custom report')
      }),
    )
  }

  delete(orgId: number, id: number): Observable<{ status: string }> {
    const url = `/api/v3/data_views/${id}/?organization_id=${orgId}`
    return this._httpClient.delete<{ status: string }>(url).pipe(
      tap(() => {
        this._currentReports = this._currentReports.filter((r) => r.id !== id)
        this._customReports.next(this._currentReports)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting custom report')
      }),
    )
  }

  evaluate(orgId: number, id: number, columns: number[]): Observable<CustomReportEvaluateResponse['data']> {
    const url = `/api/v3/data_views/${id}/evaluate/?organization_id=${orgId}`
    return this._httpClient.post<CustomReportEvaluateResponse>(url, { columns }).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error evaluating custom report')
      }),
    )
  }
}
