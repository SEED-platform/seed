import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { BehaviorSubject, catchError, map, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type {
  ReportConfiguration,
  ReportConfigurationResponse,
  ReportConfigurationsResponse,
  ReportConfigurationUpsertPayload,
} from './report-configuration.types'

@Injectable({ providedIn: 'root' })
export class ReportConfigurationService {
  private _errorService = inject(ErrorService)
  private _httpClient = inject(HttpClient)
  private _reportConfigurations = new BehaviorSubject<ReportConfiguration[]>([])
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)

  reportConfigurations$ = this._reportConfigurations.asObservable()

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
    const url = `/api/v3/organizations/${orgId}/report_configurations`
    this._httpClient
      .get<ReportConfigurationsResponse>(url)
      .pipe(
        map(({ data }) => {
          const configs = data.toSorted((a, b) => naturalSort(a.name, b.name))
          this._reportConfigurations.next(configs)
          return configs
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching report configurations')
        }),
      )
      .subscribe()
  }

  create(orgId: number, data: ReportConfigurationUpsertPayload): Observable<ReportConfiguration> {
    const url = `/api/v3/report_configurations/?organization_id=${orgId}`
    return this._httpClient.post<ReportConfigurationResponse>(url, data).pipe(
      map(({ data: config }) => config),
      tap(() => {
        this.list(orgId)
        this._snackBar.success('Created report configuration')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating report configuration')
      }),
    )
  }

  update(orgId: number, id: number, data: ReportConfigurationUpsertPayload): Observable<ReportConfiguration> {
    const url = `/api/v3/report_configurations/${id}/?organization_id=${orgId}`
    return this._httpClient.put<ReportConfigurationResponse>(url, data).pipe(
      map(({ data: config }) => config),
      tap(() => {
        this.list(orgId)
        this._snackBar.success('Updated report configuration')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating report configuration')
      }),
    )
  }

  delete(orgId: number, id: number): Observable<unknown> {
    const url = `/api/v3/report_configurations/${id}/?organization_id=${orgId}`
    return this._httpClient.delete(url, { observe: 'response' }).pipe(
      tap(() => {
        this.list(orgId)
        this._snackBar.success('Deleted report configuration')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting report configuration')
      }),
    )
  }
}
