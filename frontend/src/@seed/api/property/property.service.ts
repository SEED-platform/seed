import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError } from 'rxjs'
import { ErrorService } from '@seed/services'
import type { PropertyColumnSummaryResponse } from './property.types'

@Injectable({ providedIn: 'root' })
export class PropertyService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)

  columnSummary(orgId: number, cycleIds: number[], columnNames: string[] | 'all' = 'all'): Observable<PropertyColumnSummaryResponse> {
    const url = '/api/v4/properties/column_summary/'
    const params = {
      organization_id: orgId,
      cycle_ids: cycleIds.join(','),
      column_names: columnNames === 'all' ? 'all' : columnNames.join(','),
    }

    return this._httpClient.get<PropertyColumnSummaryResponse>(url, { params }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching property column summary')
      }),
    )
  }
}
