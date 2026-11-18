import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { BehaviorSubject, catchError, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { OrganizationService } from '../organization'
import type { Meter, MeterConfig, MeterUsage } from './meter.types'

@Injectable({ providedIn: 'root' })
export class MeterService {
  private _errorService = inject(ErrorService)
  private _meters = new BehaviorSubject<Meter[]>([])
  private _meterReadings = new BehaviorSubject<MeterUsage>(null)
  private _httpClient = inject(HttpClient)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)

  meters$ = this._meters.asObservable()
  meterReadings$ = this._meterReadings.asObservable()

  list(orgId: number, viewId: number) {
    const url = `/api/v3/properties/${viewId}/meters/?organization_id=${orgId}`
    this._httpClient
      .get<Meter[]>(url)
      .pipe(
        take(1),
        tap((meters) => {
          this._meters.next(meters)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching meters')
        }),
      )
      .subscribe()
  }

  listReadings(orgId: number, viewId: number, interval: string, excluded_meter_ids: number[] = []) {
    const url = `/api/v3/properties/${viewId}/meter_usage/?organization_id=${orgId}`
    const body = { interval, excluded_meter_ids }
    return this._httpClient
      .post<MeterUsage>(url, body)
      .pipe(
        take(1),
        tap((readings) => {
          this._meterReadings.next(readings)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching meter usage')
        }),
      )
      .subscribe()
  }

  delete(orgId: number, viewId: number, meterId: number) {
    const url = `/api/v3/properties/${viewId}/meters/${meterId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Meter deleted successfully')
        this.list(orgId, viewId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting meter')
      }),
    )
  }

  updateMeterConnection(orgId: number, meterId: number, meter_config: MeterConfig, viewId: number = null, groupId: number = null) {
    if (!viewId && !groupId) {
      throw new Error('Either viewId or groupId is required')
    }
    const url = viewId
      ? `/api/v3/properties/${viewId}/meters/${meterId}/update_connection/?organization_id=${orgId}`
      : `/api/v3/inventory_groups/${groupId}/meters/${meterId}/update_connection/?organization_id=${orgId}`

    return this._httpClient.put(url, { meter_config }).pipe(
      tap(() => {
        this._snackBar.success('Meter connection updated successfully')
        if (viewId) {
          this.list(orgId, viewId)
        } else if (groupId) {
          console.log('todo: get group meters')
        }
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating meter connection')
      }),
    )
  }
}
