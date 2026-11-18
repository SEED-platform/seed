import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { BehaviorSubject, catchError, map, type Observable, of, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory'
import { OrganizationService } from '../organization'
import type {
  GroupDashboard,
  GroupDashboardResponse,
  GroupMeter,
  GroupMetersResponse,
  GroupMeterUsageResponse,
  GroupPropertiesResponse,
  GroupProperty,
  GroupSankeyEntry,
  GroupSankeyResponse,
  GroupService,
  GroupServiceDetail,
  GroupSystem,
  InventoryGroup,
  InventoryGroupResponse,
  MeterInterval,
  MeterReadingDetail,
  SystemsByTypeResponse,
} from './groups.types'

@Injectable({ providedIn: 'root' })
export class GroupsService {
  private _errorService = inject(ErrorService)
  private _groups = new BehaviorSubject<InventoryGroup[]>([])
  private _httpClient = inject(HttpClient)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)

  groups$ = this._groups.asObservable()

  list(orgId: number) {
    const url = `/api/v3/inventory_groups/?organization_id=${orgId}`
    this._httpClient
      .get<InventoryGroup[]>(url)
      .pipe(
        take(1),
        map((data) => {
          const groups = Array.isArray(data) ? data : []
          this._groups.next(groups)
          return groups
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching groups')
        }),
      )
      .subscribe()
  }

  // inventoryIds (Property/TaxLot[]) are not viewIds
  listForInventory(orgId: number, inventoryIds: number[], type: InventoryType) {
    const url = `/api/v3/inventory_groups/filter/?organization_id=${orgId}&inventory_type=${type}`
    const body = { selected: inventoryIds }
    this._httpClient
      .post<InventoryGroup[]>(url, body)
      .pipe(
        take(1),
        map((data) => {
          const groups = Array.isArray(data) ? data : []
          this._groups.next(groups)
          return groups
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching groups for inventory')
        }),
      )
      .subscribe()
  }

  fetchGroups(orgId: number): Observable<InventoryGroup[]> {
    const url = `/api/v3/inventory_groups/?organization_id=${orgId}`
    return this._httpClient.get<InventoryGroup[]>(url).pipe(
      map((data) => (Array.isArray(data) ? data : [])),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching groups')
      }),
    )
  }

  create(orgId: number, data: InventoryGroup): Observable<InventoryGroup> {
    const url = `/api/v3/inventory_groups/?organization_id=${orgId}`
    return this._httpClient.post<InventoryGroupResponse>(url, data).pipe(
      map(({ data }) => {
        this._snackBar.success('Group created successfully')
        this.list(orgId)
        return data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating group')
      }),
    )
  }

  get(orgId: number, id: number): Observable<InventoryGroup> {
    const url = `/api/v3/inventory_groups/${id}/?organization_id=${orgId}`
    return this._httpClient.get<InventoryGroupResponse>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching group')
      }),
    )
  }

  update(orgId: number, id: number, data: InventoryGroup): Observable<InventoryGroup> {
    const url = `/api/v3/inventory_groups/${id}/?organization_id=${orgId}`
    return this._httpClient.put<InventoryGroupResponse>(url, data).pipe(
      map(({ data }) => {
        this._snackBar.success('Group updated successfully')
        this.list(orgId)
        return data
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating group')
      }),
    )
  }

  delete(orgId: number, id: number): Observable<unknown> {
    const url = `/api/v3/inventory_groups/${id}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Group deleted successfully')
        this.list(orgId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting group')
      }),
    )
  }

  bulkUpdate(
    orgId: number,
    addGroupIds: number[],
    removeGroupIds: number[],
    viewIds: number[],
    type: 'property' | 'tax_lot',
  ): Observable<unknown> {
    const url = `/api/v3/inventory_group_mappings/put/?organization_id=${orgId}`
    const data = {
      inventory_ids: viewIds,
      add_group_ids: addGroupIds,
      remove_group_ids: removeGroupIds,
      inventory_type: type,
    }
    return this._httpClient.put(url, data).pipe(
      tap(() => {
        this.list(orgId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating groups')
      }),
    )
  }

  getById(orgId: number, groupId: number): Observable<InventoryGroup> {
    const url = `/api/v3/inventory_groups/${groupId}/?organization_id=${orgId}`
    return this._httpClient.get<InventoryGroupResponse>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching group')
      }),
    )
  }

  getDashboard(orgId: number, groupId: number, cycleId: number): Observable<GroupDashboard> {
    const url = `/api/v3/inventory_groups/${groupId}/dashboard/?organization_id=${orgId}&cycle_id=${cycleId}`
    return this._httpClient.get<GroupDashboardResponse>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching group dashboard')
      }),
    )
  }

  getSankeyData(orgId: number, groupId: number, cycleId: number, meterType: string): Observable<GroupSankeyEntry[]> {
    const url = `/api/v3/inventory_groups/${groupId}/dashboard_sankey/?organization_id=${orgId}&cycle_id=${cycleId}&meter_type=${meterType}`
    return this._httpClient.get<GroupSankeyResponse>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching sankey data')
      }),
    )
  }

  getProperties(orgId: number, groupId: number): Observable<GroupProperty[]> {
    const url = `/api/v3/inventory_groups/${groupId}/properties/?organization_id=${orgId}`
    return this._httpClient.get<GroupPropertiesResponse>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching group properties')
      }),
    )
  }

  getMeters(orgId: number, groupId: number): Observable<GroupMeter[]> {
    const url = `/api/v3/inventory_groups/${groupId}/meters/?organization_id=${orgId}`
    return this._httpClient.get<GroupMetersResponse>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching group meters')
      }),
    )
  }

  getMeterUsage(orgId: number, groupId: number, interval: MeterInterval): Observable<GroupMeterUsageResponse['data']> {
    const url = `/api/v3/inventory_groups/${groupId}/meter_usage/?organization_id=${orgId}`
    return this._httpClient.post<GroupMeterUsageResponse>(url, { interval }).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching meter usage')
      }),
    )
  }

  getMeterReadings(orgId: number, meterId: number): Observable<MeterReadingDetail[]> {
    const url = `/api/v4/meters/${meterId}/readings/?organization_id=${orgId}`
    return this._httpClient.get<{ status: string; data: MeterReadingDetail[]; count: number }>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching meter readings')
      }),
    )
  }

  getMeterReadingsCount(orgId: number, meterId: number): Observable<number> {
    const url = `/api/v4/meters/${meterId}/readings/count/?organization_id=${orgId}`
    return this._httpClient.get<{ status: string; data: { count: number } }>(url).pipe(
      map(({ data }) => data.count),
      catchError(() => of(0)),
    )
  }

  createMeter(orgId: number, groupId: number, meterData: Partial<GroupMeter>): Observable<GroupMeter> {
    const url = `/api/v3/inventory_groups/${groupId}/meters/?organization_id=${orgId}`
    return this._httpClient.post<GroupMeter>(url, meterData).pipe(
      tap(() => {
        this._snackBar.success('Meter created successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating meter')
      }),
    )
  }

  // Systems CRUD
  getSystemsByType(orgId: number, groupId: number): Observable<Record<string, GroupSystem[]>> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/systems_by_type/?organization_id=${orgId}`
    return this._httpClient.get<SystemsByTypeResponse>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching systems')
      }),
    )
  }

  createSystem(orgId: number, groupId: number, systemData: Partial<GroupSystem>): Observable<GroupSystem> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/?organization_id=${orgId}`
    return this._httpClient.post<GroupSystem>(url, systemData).pipe(
      tap(() => {
        this._snackBar.success('System created successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating system')
      }),
    )
  }

  updateSystem(orgId: number, groupId: number, systemId: number, systemData: Partial<GroupSystem>): Observable<GroupSystem> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/?organization_id=${orgId}`
    return this._httpClient.put<GroupSystem>(url, systemData).pipe(
      tap(() => {
        this._snackBar.success('System updated successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating system')
      }),
    )
  }

  deleteSystem(orgId: number, groupId: number, systemId: number): Observable<unknown> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('System deleted successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting system')
      }),
    )
  }

  // Services CRUD
  getServices(orgId: number, groupId: number, systemId: number): Observable<GroupService[]> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/services/?organization_id=${orgId}`
    return this._httpClient.get<{ status: string; data: GroupService[] }>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching services')
      }),
    )
  }

  createService(orgId: number, groupId: number, systemId: number, serviceData: Partial<GroupService>): Observable<GroupService> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/services/?organization_id=${orgId}`
    return this._httpClient.post<GroupService>(url, serviceData).pipe(
      tap(() => {
        this._snackBar.success('Service created successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating service')
      }),
    )
  }

  updateService(
    orgId: number,
    groupId: number,
    systemId: number,
    serviceId: number,
    serviceData: Partial<GroupService>,
  ): Observable<GroupService> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/services/${serviceId}/?organization_id=${orgId}`
    return this._httpClient.put<GroupService>(url, serviceData).pipe(
      tap(() => {
        this._snackBar.success('Service updated successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating service')
      }),
    )
  }

  deleteService(orgId: number, groupId: number, systemId: number, serviceId: number): Observable<unknown> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/services/${serviceId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Service deleted successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting service')
      }),
    )
  }

  getServiceDetail(orgId: number, groupId: number, systemId: number, serviceId: number) {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/services/${serviceId}/?organization_id=${orgId}`
    return this._httpClient.get<GroupServiceDetail>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching service detail')
      }),
    )
  }

  createServiceMeters(
    orgId: number,
    groupId: number,
    systemId: number,
    serviceId: number,
    data: { direction: string; type: string; property_ids: number[] },
  ): Observable<unknown> {
    const url = `/api/v3/inventory_groups/${groupId}/systems/${systemId}/services/${serviceId}/create_meters/?organization_id=${orgId}`
    return this._httpClient.post(url, data).pipe(
      tap(() => {
        this._snackBar.success('Meters created successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating service meters')
      }),
    )
  }

  updateMeter(
    orgId: number,
    groupId: number,
    meterId: number,
    data: { alias?: string; connection_config?: Record<string, unknown> },
  ): Observable<unknown> {
    const url = `/api/v3/inventory_groups/${groupId}/meters/${meterId}/?organization_id=${orgId}`
    return this._httpClient.put(url, data).pipe(
      tap(() => {
        this._snackBar.success('Meter updated successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating meter')
      }),
    )
  }

  deleteMeter(orgId: number, groupId: number, meterId: number): Observable<unknown> {
    const url = `/api/v3/inventory_groups/${groupId}/meters/${meterId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Meter deleted successfully')
      }),
      catchError((error: HttpErrorResponse) => {
        // Dev proxy may fail to parse 204 No Content (status 0). The delete succeeds server-side.
        if (error.status === 0) {
          this._snackBar.success('Meter deleted successfully')
          return of(null)
        }
        return this._errorService.handleError(error, 'Error deleting meter')
      }),
    )
  }

  uploadMeterReadings(orgId: number, importFileId: number, meterId: number): Observable<{ message: string }> {
    const url = `/api/v3/import_files/${importFileId}/system_meter_upload/?organization_id=${orgId}`
    return this._httpClient.post<{ message: string }>(url, { meter_id: meterId }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error uploading meter readings')
      }),
    )
  }
}
