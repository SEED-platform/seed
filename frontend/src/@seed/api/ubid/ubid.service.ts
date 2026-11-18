import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType, InventoryTypeSingular } from 'app/modules/inventory/inventory.types'
import { UserService } from '../user'
import type { DecodeResults, Ubid, UbidDetails, UbidResponse, ValidateUbidResponse } from './ubid.types'

@Injectable({ providedIn: 'root' })
export class UbidService {
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)
  private _ubids = new ReplaySubject<Ubid[]>()
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)

  ubids$ = this._ubids.asObservable()

  list(orgId: number, viewId: number, type: InventoryType) {
    const typeMap: Record<InventoryType, InventoryTypeSingular> = { properties: 'property', taxlots: 'taxlot' }
    const singularType = typeMap[type]
    const url = `/api/v3/ubid/ubids_by_view/?organization_id=${orgId}`
    const body = { view_id: viewId, type: singularType }
    this._httpClient
      .post<UbidResponse>(url, body)
      .pipe(
        take(1),
        map(({ data }) => data),
        tap((ubids) => {
          this._ubids.next(ubids)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching UBIDs')
        }),
      )
      .subscribe()
  }

  delete(orgId: number, viewId: number, ubidId: number, type: InventoryType): Observable<object> {
    const url = `/api/v3/ubid/${ubidId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this.list(orgId, viewId, type)
        this._snackBar.success('UBID deleted successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting UBID')
      }),
    )
  }

  update(orgId: number, viewId: number, ubidId: number, ubid_details: UbidDetails, type: InventoryType): Observable<Ubid> {
    const url = `/api/v3/ubid/${ubidId}/?organization_id=${orgId}`
    return this._httpClient.put<Ubid>(url, ubid_details).pipe(
      tap(() => {
        this.list(orgId, viewId, type)
        this._snackBar.success('UBID updated successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating UBID')
      }),
    )
  }

  create(orgId: number, viewId: number, ubid_details: UbidDetails, type: InventoryType): Observable<Ubid> {
    const url = `/api/v3/ubid/?organization_id=${orgId}`
    return this._httpClient.post<Ubid>(url, ubid_details).pipe(
      tap(() => {
        this.list(orgId, viewId, type)
        this._snackBar.success('UBID created successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating UBID')
      }),
    )
  }

  /* DEVELOPER NOTE
  / Old seed uses UniqueBuildingIdentification, but Im not sure how that was defined
  / ubid_service.js: ubid_factory.validate_ubid_js = (ubid) => UniqueBuildingIdentification.v3.isValid(ubid);
  */
  validate(orgId: number, ubid: string): Observable<boolean> {
    const url = `/api/v3/ubid/validate_ubid/?organization_id=${orgId}`
    return this._httpClient.post<ValidateUbidResponse>(url, { ubid }).pipe(
      map(({ data }) => data.valid),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error validating UBID')
      }),
    )
  }

  decodeResults(orgId: number, viewIds: number[], type: InventoryType): Observable<DecodeResults> {
    const url = `/api/v3/ubid/decode_results/?organization_id=${orgId}`
    const data = {
      property_view_ids: type === 'properties' ? viewIds : [],
      taxlot_view_ids: type === 'taxlots' ? viewIds : [],
    }
    return this._httpClient.post<DecodeResults>(url, data).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching UBID decode results')
      }),
    )
  }

  decodeByIds(orgId: number, viewIds: number[], type: InventoryType): Observable<{ status: string }> {
    const url = `/api/v3/ubid/decode_by_ids/?organization_id=${orgId}`
    const data = {
      property_view_ids: type === 'properties' ? viewIds : [],
      taxlot_view_ids: type === 'taxlots' ? viewIds : [],
    }
    return this._httpClient.post<{ status: string }>(url, data).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error decoding UBIDs by ID')
      }),
    )
  }

  compareUbids(orgId: number, ubid1: string, ubid2: string): Observable<number> {
    const url = `/api/v3/ubid/get_jaccard_index/?organization_id=${orgId}`
    return this._httpClient.post<{ status: string; data: number }>(url, { ubid1, ubid2 }).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error comparing UBIDs')
      }),
    )
  }

  getUbidModelsByView(orgId: number, viewId: number, type: InventoryType): Observable<Ubid[]> {
    const url = `/api/v3/ubid/ubids_by_view/?organization_id=${orgId}`
    const data = {
      view_id: viewId,
      type: type === 'taxlots' ? 'taxlot' : 'property',
    }
    return this._httpClient.post<{ status: string; data: Ubid[] }>(url, data).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching UBID models')
      }),
    )
  }
}
