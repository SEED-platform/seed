import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Injectable({ providedIn: 'root' })
export class PairingService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)

  pairInventory(orgId: number, viewId: number, otherViewId: number, inventoryType: InventoryType): Observable<unknown> {
    const url
      = inventoryType === 'taxlots'
        ? `/api/v3/taxlots/${viewId}/pair/?organization_id=${orgId}&property_id=${otherViewId}`
        : `/api/v3/properties/${viewId}/pair/?organization_id=${orgId}&taxlot_id=${otherViewId}`

    return this._httpClient.put<unknown>(url, {}).pipe(
      tap(() => {
        this._snackBar.success('Paired successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error pairing inventory')
      }),
    )
  }

  unpairInventory(orgId: number, viewId: number, otherViewId: number, inventoryType: InventoryType): Observable<unknown> {
    const url
      = inventoryType === 'taxlots'
        ? `/api/v3/taxlots/${viewId}/unpair/?organization_id=${orgId}&property_id=${otherViewId}`
        : `/api/v3/properties/${viewId}/unpair/?organization_id=${orgId}&taxlot_id=${otherViewId}`

    return this._httpClient.put<unknown>(url, {}).pipe(
      tap(() => {
        this._snackBar.success('Unpaired successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error unpairing inventory')
      }),
    )
  }
}
