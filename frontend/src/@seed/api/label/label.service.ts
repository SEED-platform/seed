import type { HttpErrorResponse, HttpResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject, switchMap, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType, InventoryTypeSingular } from 'app/modules/inventory/inventory.types'
import { UserService } from '../user'
import type { Label, PropertyViewLabel } from './label.types'

@Injectable({ providedIn: 'root' })
export class LabelService {
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)
  private _labels = new ReplaySubject<Label[]>(1)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)

  labels$ = this._labels.asObservable()

  constructor() {
    // Fetch current org data whenever user org id changes
    this._userService.currentOrganizationId$.pipe(switchMap((organizationId) => this.getByOrgId(organizationId))).subscribe()
  }

  getByOrgId(organizationId: number): Observable<Label[]> {
    const url = `/api/v3/labels/?organization_id=${organizationId}`
    return this._httpClient.get<Label[]>(url).pipe(
      map((response) => {
        const labels = response.sort((a, b) => naturalSort(a.name, b.name))
        this._labels.next(labels)
        return labels
      }),
      catchError((error: HttpErrorResponse) => {
        // TODO need to figure out error handling
        return this._errorService.handleError(error, 'Error fetching organization')
      }),
    )
  }

  /*
   * Get inventory labels for a list of views
   */
  getInventoryLabels(orgId: number, viewIds: number[], cycleId: number, inventoryType: InventoryType): Observable<Label[]> {
    return inventoryType === 'taxlots' ? this.getTaxLotLabels(orgId, viewIds, cycleId) : this.getPropertyLabels(orgId, viewIds, cycleId)
  }

  getPropertyLabels(orgId: number, viewIds: number[], cycleId: number): Observable<Label[]> {
    const url = '/api/v3/properties/labels/'
    const data = { selected: viewIds }
    const params = { organization_id: orgId, cycle_id: cycleId }
    return this._httpClient.post<Label[]>(url, data, { params }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching labels: ${error.message}`)
      }),
    )
  }

  getTaxLotLabels(orgId: number, viewIds: number[], cycleId: number): Observable<Label[]> {
    const url = '/api/v3/properties/labels/'
    const data = { selected: viewIds }
    const params = { organization_id: orgId, cycle_id: cycleId }
    return this._httpClient.post<Label[]>(url, data, { params }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching labels: ${error.message}`)
      }),
    )
  }

  get(orgId: number, id: number): Observable<Label> {
    const url = `/api/v3/labels/${id}/?organization_id=${orgId}`
    return this._httpClient.get<Label>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching label: ${error.message}`)
      }),
    )
  }

  create(label: Label): Observable<Label> {
    const url = `/api/v3/labels/?organization_id=${label.organization_id}`
    return this._httpClient.post<Label>(url, { ...label }).pipe(
      tap(() => {
        this._snackBar.success('Label Created')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error creating label: ${error.message}`)
      }),
    )
  }

  update(label: Label): Observable<Label> {
    const url = `/api/v3/labels/${label.id}/?organization_id=${label.organization_id}`
    return this._httpClient.put<Label>(url, { ...label }).pipe(
      map((response) => {
        this._snackBar.success('Label Mapping Updated')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error updating label: ${error.message}`)
      }),
    )
  }

  delete(label: Label): Observable<HttpResponse<null>> {
    const url = `/api/v3/labels/${label.id}/?organization_id=${label.organization_id}`
    return this._httpClient.delete<HttpResponse<null>>(url).pipe(
      map((response) => {
        this._snackBar.success('Label Deleted')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error deleting label: ${error.message}`)
      }),
    )
  }

  bulkUpdate(organizationId: number, labels: Label[], show_in_list: boolean): Observable<HttpResponse<null>> {
    const url = `/api/v3/labels/bulk_update/?organization_id=${organizationId}`
    return this._httpClient.put<HttpResponse<null>>(url, { data: { show_in_list }, label_ids: labels.map((l) => l.id) }).pipe(
      map((response) => {
        this._snackBar.success(`All labels ${show_in_list ? 'shown' : 'hidden'}`)
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error updating labels: ${error.message}`)
      }),
    )
  }

  updateLabelInventory(
    orgId: number,
    viewIds: number[],
    type: InventoryType,
    addLabelIds: number[],
    removeLabelIds: number[],
  ): Observable<HttpResponse<null>> {
    const singularType: InventoryTypeSingular = type === 'taxlots' ? 'taxlot' : 'property'
    const url = `/api/v3/labels_${singularType}/?organization_id=${orgId}`
    const data = { inventory_ids: viewIds, add_label_ids: addLabelIds, remove_label_ids: removeLabelIds }
    return this._httpClient.put<HttpResponse<null>>(url, data).pipe(
      map((response) => {
        this._snackBar.success('Labels updated for inventory')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error updating label inventory: ${error.message}`)
      }),
    )
  }

  listByCycleGoal(orgId: number, goalId: number, cycleId: number): Observable<PropertyViewLabel[]> {
    const url = `/api/v3/property_view_labels/list_by_cycle_goal/?organization_id=${orgId}&goal_id=${goalId}&cycle_id=${cycleId}`
    return this._httpClient.get<PropertyViewLabel[]>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching labels: ${error.message}`)
      }),
    )
  }
}
