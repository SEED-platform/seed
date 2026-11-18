import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError } from 'rxjs'
import { ErrorService } from '@seed/services'
import type { InventoryType } from 'app/modules/inventory'
import type { ConfidenceSummary, GeocodingColumns } from './geocode.types'

@Injectable({ providedIn: 'root' })
export class GeocodeService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)

  geocode(orgId: number, viewIds: number[], type: InventoryType): Observable<unknown> {
    const url = `/api/v3/geocode/geocode_by_ids/?organization_id=${orgId}`
    const data = {
      property_view_ids: type === 'taxlots' ? [] : viewIds,
      taxlot_view_ids: type === 'taxlots' ? viewIds : [],
    }
    return this._httpClient.post(url, data).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Geocode Error')
      }),
    )
  }

  confidenceSummary(orgId: number, viewIds: number[], type: InventoryType): Observable<ConfidenceSummary> {
    const url = `/api/v3/geocode/confidence_summary/?organization_id=${orgId}`
    const data = {
      property_view_ids: type === 'taxlots' ? [] : viewIds,
      taxlot_view_ids: type === 'taxlots' ? viewIds : [],
    }
    return this._httpClient.post<ConfidenceSummary>(url, data).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Geocode Confidence Summary Error')
      }),
    )
  }

  checkApiKey(orgId: number): Observable<boolean> {
    const url = `/api/v3/organizations/${orgId}/geocode_api_key_exists/`
    return this._httpClient.get<boolean>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Geocode API Key Check Error')
      }),
    )
  }

  geocodingEnabled(orgId: number): Observable<boolean> {
    const url = `/api/v3/organizations/${orgId}/geocoding_enabled/`
    return this._httpClient.get<boolean>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Geocoding Enabled Check Error')
      }),
    )
  }

  geocodingColumns(orgId: number): Observable<GeocodingColumns> {
    const url = `/api/v3/organizations/${orgId}/geocoding_columns/`
    return this._httpClient.get<GeocodingColumns>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Geocoding Columns Error')
      }),
    )
  }
}
