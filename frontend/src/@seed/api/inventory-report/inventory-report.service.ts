import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient, HttpParams } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map } from 'rxjs'
import { ErrorService } from '@seed/services'
import type { AggregatedReportDataResponse, ReportDataResponse } from './inventory-report.types'

@Injectable({ providedIn: 'root' })
export class InventoryReportService {
  private _errorService = inject(ErrorService)
  private _httpClient = inject(HttpClient)

  getReportData(
    orgId: number,
    xVar: string,
    yVar: string,
    cycleIds: number[],
    accessLevelInstanceId: number | null,
    filterGroupId: number | null,
  ): Observable<ReportDataResponse['data']> {
    const url = `/api/v3/organizations/${orgId}/report/`
    let params = new HttpParams().set('x_var', xVar).set('y_var', yVar)
    for (const id of cycleIds) {
      params = params.append('cycle_ids', id)
    }
    if (accessLevelInstanceId != null) params = params.set('access_level_instance_id', accessLevelInstanceId)
    if (filterGroupId != null) params = params.set('filter_group_id', filterGroupId)

    return this._httpClient.get<ReportDataResponse>(url, { params }).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching report data')
      }),
    )
  }

  getAggregatedReportData(
    orgId: number,
    xVar: string,
    yVar: string,
    cycleIds: number[],
    accessLevelInstanceId: number | null,
    filterGroupId: number | null,
    aggregationType: string,
  ): Observable<AggregatedReportDataResponse['aggregated_data']> {
    const url = `/api/v3/organizations/${orgId}/report_aggregated/`
    let params = new HttpParams().set('x_var', xVar).set('y_var', yVar).set('aggregationType', aggregationType)
    for (const id of cycleIds) {
      params = params.append('cycle_ids', id)
    }
    if (accessLevelInstanceId != null) params = params.set('access_level_instance_id', accessLevelInstanceId)
    if (filterGroupId != null) params = params.set('filter_group_id', filterGroupId)

    return this._httpClient.get<AggregatedReportDataResponse>(url, { params }).pipe(
      map(({ aggregated_data }) => aggregated_data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching aggregated report data')
      }),
    )
  }

  exportReportData(
    orgId: number,
    xVar: string,
    xLabel: string,
    yVar: string,
    yLabel: string,
    cycleIds: number[],
    filterGroupId: number | null,
  ): Observable<Blob> {
    const url = `/api/v3/organizations/${orgId}/report_export/`
    let params = new HttpParams().set('x_var', xVar).set('x_label', xLabel).set('y_var', yVar).set('y_label', yLabel)
    for (const id of cycleIds) {
      params = params.append('cycle_ids', id)
    }
    if (filterGroupId != null) params = params.set('filter_group_id', filterGroupId)

    return this._httpClient.get(url, { params, responseType: 'arraybuffer' }).pipe(
      map((buffer) => new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error exporting report data')
      }),
    )
  }
}
