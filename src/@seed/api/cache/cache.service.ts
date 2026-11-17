import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError } from 'rxjs'
import { ErrorService } from '@seed/services'

@Injectable({ providedIn: 'root' })
export class CacheService {
  private _errorService = inject(ErrorService)
  private _httpClient = inject(HttpClient)

  getCacheEntry(orgId: number, uniqueId: number | string): Observable<unknown> {
    const url = `/api/v3/cache_entries/${uniqueId}/?organization_id=${orgId}`
    return this._httpClient.get<unknown>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching cache entry')
      }),
    )
  }
}
