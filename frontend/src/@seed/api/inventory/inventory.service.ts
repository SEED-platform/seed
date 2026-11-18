import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { BehaviorSubject, catchError, map, of, take, tap, throwError } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type {
  CrossCyclesResponse,
  DeleteParams,
  FilterResponse,
  FormCreateResponse,
  GenericView,
  GenericViewsResponse,
  InventoryDisplayType,
  InventoryExportData,
  InventoryFormCreateData,
  InventoryType,
  InventoryTypeGoal,
  NewProfileData,
  Profile,
  ProfileResponse,
  ProfilesResponse,
  PropertyDocumentExtension,
  UpdateInventoryResponse,
  ViewResponse,
} from 'app/modules/inventory/inventory.types'
import type { ProgressResponse } from '../progress'
import { UserService } from '../user'

@Injectable({ providedIn: 'root' })
export class InventoryService {
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)
  private _snackBar = inject(SnackBarService)
  private _errorService = inject(ErrorService)
  private _properties = new BehaviorSubject<unknown>([])
  private _columnListProfiles = new BehaviorSubject<unknown>([])
  private _view = new BehaviorSubject<ViewResponse>(null)
  orgId: number

  columnListProfiles$ = this._columnListProfiles.asObservable()
  properties$ = this._properties.asObservable()
  view$ = this._view.asObservable()

  constructor() {
    this._userService.currentOrganizationId$.subscribe((id) => (this.orgId = id))
  }

  getAgInventory(paramString: string, data: Record<string, unknown>): Observable<FilterResponse> {
    const url = `/api/v4/tax_lot_properties/filter/?${paramString}`
    return this._httpClient.post<FilterResponse>(url, data).pipe(
      map((response) => response),
      tap((response) => {
        this._properties.next(response)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching properties')
      }),
    )
  }

  getRecordCount(organization_id: number, cycle_id: number, inventory_type: InventoryTypeGoal): Observable<number> {
    const url = '/api/v4/tax_lot_properties/record_count/'
    const params = { organization_id, cycle_id, inventory_type }
    return this._httpClient.get<{ status: string; data: number }>(url, { params }).pipe(
      map((response) => response.data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching record count')
      }),
    )
  }

  getColumnListProfiles(profileLocation: string, inventoryType: string, brief = false): Observable<Profile[]> {
    const url = '/api/v3/column_list_profiles/'
    const params = {
      organization_id: this.orgId,
      inventory_type: inventoryType,
      profile_location: profileLocation,
      brief,
    }
    return this._httpClient.get<ProfilesResponse>(url, { params }).pipe(
      map((response) => response.data),
      tap((profiles) => {
        this._columnListProfiles.next(profiles)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching column list profiles')
      }),
    )
  }

  getColumnListProfile(id: number): Observable<Profile> {
    const url = `/api/v3/column_list_profiles/${id}/`
    const params = { organization_id: this.orgId }
    return this._httpClient.get<ProfileResponse>(url, { params }).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching column list profile')
      }),
    )
  }

  updateProfileToShowPopulatedColumns(
    orgId: number,
    id: number,
    cycle_id: number,
    inventory_type: InventoryDisplayType,
  ): Observable<Profile> {
    const url = `/api/v3/column_list_profiles/${id}/show_populated/?organization_id=${orgId}`
    const data = { cycle_id, inventory_type }
    return this._httpClient.put<ProfileResponse>(url, data).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating column list profile')
      }),
    )
  }

  createColumnListProfile(orgId: number, data: NewProfileData): Observable<Profile> {
    const url = `/api/v3/column_list_profiles/?organization_id=${orgId}`
    return this._httpClient.post<ProfileResponse>(url, data).pipe(
      tap(() => {
        this._snackBar.success('Profile created successfully')
      }),
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating column list profile')
      }),
    )
  }

  updateColumnListProfile(orgId: number, id: number, data: unknown): Observable<Profile> {
    const url = `/api/v3/column_list_profiles/${id}/?organization_id=${orgId}`
    return this._httpClient.put<ProfileResponse>(url, data).pipe(
      tap(() => {
        this._snackBar.success('Profile updated successfully')
      }),
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating column list profile')
      }),
    )
  }

  deleteColumnListProfile(orgId: number, id: number): Observable<null> {
    const url = `/api/v3/column_list_profiles/${id}/?organization_id=${orgId}`
    return this._httpClient.delete<null>(url).pipe(
      map((): null => null),
      catchError((error: HttpErrorResponse) => {
        // Dev proxy may fail to parse 204 No Content (status 0). The delete succeeds server-side.
        if (error.status === 0) {
          return of(null)
        }
        return this._errorService.handleError(error, 'Error deleting column list profile')
      }),
    )
  }

  deletePropertyStates({ orgId, viewIds }: DeleteParams): Observable<object> {
    const url = '/api/v3/properties/batch_delete/'
    const data = { property_view_ids: viewIds }
    const options = { params: { organization_id: orgId }, body: data }
    return this._httpClient.delete(url, options).pipe(
      tap(() => {
        this._snackBar.success('Property states deleted')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting property states')
      }),
    )
  }

  deleteTaxlotStates({ orgId, viewIds }: DeleteParams): Observable<object> {
    const url = '/api/v3/taxlots/batch_delete/'
    const data = { taxlot_view_ids: viewIds }
    const options = { params: { organization_id: orgId }, body: data }
    return this._httpClient.delete(url, options).pipe(
      tap(() => {
        this._snackBar.success('Tax lot states deleted')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting tax lot states')
      }),
    )
  }

  /*
   * Get PropertyView or TaxLotView
   */
  getView(orgId: number, viewId: number, inventoryType: InventoryType): Observable<ViewResponse> {
    return inventoryType === 'taxlots' ? this.getTaxLotView(orgId, viewId) : this.getPropertyView(orgId, viewId)
  }

  getPropertyView(orgId: number, viewId: number): Observable<ViewResponse> {
    const url = `/api/v3/properties/${viewId}/`
    const params = { organization_id: orgId }
    return this._httpClient.get<ViewResponse>(url, { params }).pipe(
      tap((view) => {
        this._view.next(view)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching property')
      }),
    )
  }

  getTaxLotView(orgId: number, viewId: number): Observable<ViewResponse> {
    const url = `/api/v3/taxlots/${viewId}/`
    const params = { organization_id: orgId }
    return this._httpClient.get<ViewResponse>(url, { params }).pipe(
      tap((view) => {
        this._view.next(view)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching property')
      }),
    )
  }

  /*
   * Get PropertyViews or TaxLotViews given a Property or Taxlot id
   */
  getViews(orgId: number, id: number, inventoryType: InventoryType): Observable<GenericView[]> {
    return inventoryType === 'taxlots' ? this.getTaxLotViews(orgId, id) : this.getPropertyViews(orgId, id)
  }

  getPropertyViews(orgId: number, propertyId: number): Observable<GenericView[]> {
    const url = '/api/v3/property_views/'
    const params = { organization_id: orgId, property: propertyId }
    return this._httpClient.get<GenericViewsResponse>(url, { params }).pipe(
      map(({ property_views }) => property_views),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching property')
      }),
    )
  }

  getTaxLotViews(orgId: number, taxLotId: number): Observable<GenericView[]> {
    const url = '/api/v3/taxlot_views/'
    const params = { organization_id: orgId, taxlot: taxLotId }
    return this._httpClient.get<GenericViewsResponse>(url, { params }).pipe(
      map(({ taxlot_views }) => taxlot_views),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching taxlot')
      }),
    )
  }

  /*
   * Update a property/taxlot view's state
   */
  updateInventory(
    orgId: number,
    viewId: number,
    inventoryType: InventoryType,
    updatedStateFields: Record<string, unknown>,
  ): Observable<UpdateInventoryResponse> {
    return inventoryType === 'taxlots'
      ? this.updateTaxLot(orgId, viewId, updatedStateFields)
      : this.updateProperty(orgId, viewId, updatedStateFields)
  }

  updateProperty(orgId: number, viewId: number, state: Record<string, unknown>): Observable<UpdateInventoryResponse> {
    const url = `/api/v3/properties/${viewId}/?organization_id=${orgId}`
    return this._httpClient.put<UpdateInventoryResponse>(url, { state }).pipe(
      tap((response) => {
        this._snackBar.success(`Success! - ${response.match_link_count} Linked. ${response.match_merged_count} Merged`)
      }),
      catchError((error: HttpErrorResponse) => {
        // errors tend to be non human readable
        this._snackBar.alert('Error updating property. Check data types and try again')
        return throwError(() => error)
      }),
    )
  }

  updateTaxLot(orgId: number, viewId: number, state: Record<string, unknown>): Observable<UpdateInventoryResponse> {
    const url = `/api/v3/taxlots/${viewId}/?organization_id=${orgId}`
    return this._httpClient.put<UpdateInventoryResponse>(url, { state }).pipe(
      tap((response) => {
        this._snackBar.success(`Success! - ${response.match_link_count} Linked. ${response.match_merged_count} Merged`)
      }),
      catchError((error: HttpErrorResponse) => {
        // errors tend to be non human readable
        this._snackBar.alert('Error updating taxlot. Check data types and try again')
        return throwError(() => error)
      }),
    )
  }

  createInventory(
    data: InventoryFormCreateData,
    inventoryType: InventoryType,
    viewId: number | null = null,
  ): Observable<FormCreateResponse> {
    const url = `/api/v3/${inventoryType}/`
    const params: Record<string, number> = { organization_id: this.orgId }
    if (viewId !== null) {
      params.related_view_id = viewId
    }
    return this._httpClient.post<Record<string, unknown>>(url, data, { params }).pipe(
      map((r) => ({
        status: r.status as string,
        // normalize property_view_id / taxlot_view_id to view_id
        view_id: (r.property_view_id ?? r.taxlot_view_id ?? r.view_id ?? null) as number | null,
      })),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error creating ${inventoryType === 'taxlots' ? 'tax lot' : 'property'}`)
      }),
    )
  }

  uploadPropertyDocument(orgId: number, viewId: number, file: File, fileExt: PropertyDocumentExtension): Observable<unknown> {
    const url = `/api/v3/properties/${viewId}/upload_inventory_document/?organization_id=${orgId}`
    const formData = new FormData()
    formData.append('file', file, file.name)
    formData.append('file_type', fileExt)
    return this._httpClient.put<unknown>(url, formData).pipe(
      tap(() => {
        this._snackBar.success('Document uploaded successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error Uploading Document')
      }),
    )
  }

  deletePropertyDocument(orgId: number, viewId: number, file_id: string): Observable<object> {
    const url = `/api/v3/properties/${viewId}/delete_inventory_document/?organization_id=${orgId}&file_id=${file_id}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Document deleted successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting Document')
      }),
    )
  }

  filterByCycle(
    orgId: number,
    profileId: number | undefined,
    cycleIds: number[],
    inventoryType: InventoryType,
  ): Observable<CrossCyclesResponse> {
    const url = `/api/v3/${inventoryType}/filter_by_cycle/`
    const data = {
      organization_id: orgId,
      profile_id: profileId,
      cycle_ids: cycleIds,
    }

    return this._httpClient.post<CrossCyclesResponse>(url, data).pipe(
      // map((response) => {
      //   return response
      // }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching ${inventoryType}`)
      }),
    )
  }

  movePropertiesToAccessLevelInstance(orgId: number, aliId: number, viewIds: number[]): Observable<unknown> {
    const url = `/api/v3/properties/move_properties_to/?organization_id=${orgId}`
    const data = { property_view_ids: viewIds, access_level_instance_id: aliId }
    return this._httpClient.post(url, data).pipe(
      tap(() => {
        this._snackBar.success('Properties moved successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error moving properties')
      }),
    )
  }

  updateDerivedData(orgId: number, propertyViewIds: number[], taxlotViewIds: number[]): Observable<ProgressResponse> {
    const url = '/api/v3/tax_lot_properties/update_derived_data/'
    const data = {
      organization_id: orgId,
      property_view_ids: propertyViewIds,
      taxlot_view_ids: taxlotViewIds,
    }
    return this._httpClient.post<ProgressResponse>(url, data).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating derived data')
      }),
    )
  }

  copyToCycle(orgId: number, cycleId: number, viewIds: number[], columnIds: number[]): Observable<ProgressResponse> {
    const url = `/api/v3/properties/copy_to_cycle/?organization_id=${orgId}`
    return this._httpClient.post<ProgressResponse>(url, { cycle_id: cycleId, view_ids: viewIds, column_ids: columnIds }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error copying inventory to cycle')
      }),
    )
  }

  startInventoryExport(orgId: number, data: InventoryExportData): Observable<ProgressResponse> {
    const url = `/api/v3/tax_lot_properties/start_export/?organization_id=${orgId}`
    return this._httpClient.post<ProgressResponse>(url, data).pipe(
      take(1),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error starting export')
      }),
    )
  }

  startRefreshMetadata(orgId: number): Observable<ProgressResponse> {
    const url = `/api/v3/tax_lot_properties/start_set_update_to_now/?organization_id=${orgId}`
    return this._httpClient.get<ProgressResponse>(url).pipe(
      take(1),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error starting metadata refresh')
      }),
    )
  }

  refreshMetadata(orgId: number, propertyViews: number[], taxlotViews: number[], progressKey: string): Observable<ProgressResponse> {
    const url = '/api/v3/tax_lot_properties/set_update_to_now/'
    const data = {
      organization_id: orgId,
      property_views: propertyViews,
      taxlot_views: taxlotViews,
      progress_key: progressKey,
    }
    return this._httpClient.post<ProgressResponse>(url, data).pipe(
      take(1),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error refreshing metadata')
      }),
    )
  }

  propertiesMetersExist(orgId: number, propertyViewIds: number[]): Observable<boolean> {
    const url = `/api/v3/properties/meters_exist/?organization_id=${orgId}`
    return this._httpClient.post<boolean>(url, { property_view_ids: propertyViewIds }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error checking if meters exist for properties')
      }),
    )
  }

  evaluationExportToCts(orgId: number, viewIds: number[], filename: string): Observable<Blob> {
    const url = `/api/v3/properties/evaluation_export_to_cts/?organization_id=${orgId}`
    return this._httpClient.post(url, { filename, property_view_ids: viewIds }, { responseType: 'arraybuffer' }).pipe(
      map((response) => new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error exporting to CTS')
      }),
    )
  }

  facilityBpsExportToCts(orgId: number, viewIds: number[], filename: string): Observable<Blob> {
    const url = `/api/v3/properties/facility_bps_export_to_cts/?organization_id=${orgId}`
    return this._httpClient.post(url, { filename, property_view_ids: viewIds }, { responseType: 'arraybuffer' }).pipe(
      map((response) => new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error exporting to CTS')
      }),
    )
  }

  batchUpdatePropertyStates(orgId: number, propertyViewIds: number[], valuesByColumnId: Record<number, unknown>): Observable<unknown> {
    const url = `/api/v3/properties/batch_update/?organization_id=${orgId}`
    return this._httpClient.put(url, { property_view_ids: propertyViewIds, values_by_column_id: valuesByColumnId }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating properties')
      }),
    )
  }

  updateSalesforce(orgId: number, propertyViewIds: number[]): Observable<{ status: string; message: string }> {
    const url = `/api/v3/properties/update_salesforce/?organization_id=${orgId}`
    return this._httpClient.post<{ status: string; message: string }>(url, { property_view_ids: propertyViewIds }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating Salesforce')
      }),
    )
  }

  getBuildingSync(orgId: number, viewId: number, profileId: number): Observable<string> {
    const url = `/api/v3/properties/${viewId}/building_sync/`
    return this._httpClient.get(url, { params: { organization_id: orgId, profile_id: profileId }, responseType: 'text' }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error downloading BuildingSync file')
      }),
    )
  }

  updateWithBuildingSync(orgId: number, viewId: number, cycleId: number, file: File): Observable<{ status: string; message?: string }> {
    const url = `/api/v3/properties/${viewId}/update_with_building_sync/?cycle_id=${cycleId}&organization_id=${orgId}`
    const formData = new FormData()
    formData.append('file', file, file.name)
    formData.append('file_type', '1')
    return this._httpClient.put<{ status: string; message?: string }>(url, formData).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating property with BuildingSync')
      }),
    )
  }

  matchMergeLink(orgId: number, viewId: number, type: InventoryType): Observable<{ view_id: number }> {
    const url = `/api/v3/${type}/${viewId}/match_merge_link/?organization_id=${orgId}`
    return this._httpClient.post<{ view_id: number }>(url, {}).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error matching, merging, and linking')
      }),
    )
  }

  unmerge(orgId: number, viewId: number, type: InventoryType): Observable<{ view_id: number }> {
    const url = `/api/v3/${type}/${viewId}/unmerge/?organization_id=${orgId}`
    const request$
      = type === 'properties' ? this._httpClient.put<{ view_id: number }>(url, {}) : this._httpClient.post<{ view_id: number }>(url, {})
    return request$.pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error unmerging inventory')
      }),
    )
  }

  getEspmBuildingXlsx(orgId: number, pmPropertyId: string, username: string, password: string): Observable<ArrayBuffer> {
    const url = `/api/v3/portfolio_manager/${pmPropertyId}/download/?organization_id=${orgId}`
    return this._httpClient.post(url, { username, password }, { responseType: 'arraybuffer' }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error downloading from ESPM')
      }),
    )
  }

  updateWithEspm(
    orgId: number,
    viewId: number,
    cycleId: number,
    mappingProfileId: number,
    file: Blob | File,
    filename?: string,
  ): Observable<{ success: boolean; message?: string }> {
    const url = `/api/v3/properties/${viewId}/update_with_espm/?cycle_id=${cycleId}&organization_id=${orgId}&mapping_profile_id=${mappingProfileId}`
    const formData = new FormData()
    formData.append('file', file, filename ?? (file instanceof File ? file.name : `espm_${Date.now()}.xlsx`))
    return this._httpClient.put<{ success: boolean; message?: string }>(url, formData).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating with ESPM data')
      }),
    )
  }
}
