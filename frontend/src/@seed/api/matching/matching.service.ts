import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory'
import type { MergingResponse } from './matching.types'

@Injectable({ providedIn: 'root' })
export class MatchingService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)

  mergeInventory(orgId: number, viewIds: number[], type: InventoryType): Observable<MergingResponse> {
    const url = `/api/v3/${type}/merge/?organization_id=${orgId}`
    const key = type === 'taxlots' ? 'taxlot_view_ids' : 'property_view_ids'
    const data = { [key]: viewIds }
    return this._httpClient.post<MergingResponse>(url, data).pipe(
      tap(() => {
        this._snackBar.success('Successfully merged inventory')
      }),
      catchError(() => {
        return this._errorService.handleError(null, 'Error merging inventory')
      }),
    )
  }
}
