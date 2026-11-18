import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { BehaviorSubject, catchError, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { OrganizationService } from '../organization'
import type { DataLogger, Sensor, SensorUsage, SensorUsageRequestConfig } from './sensor.types'

@Injectable({ providedIn: 'root' })
export class SensorService {
  private _dataLoggers = new BehaviorSubject<DataLogger[]>([])
  private _errorService = inject(ErrorService)
  private _httpClient = inject(HttpClient)
  private _organizationService = inject(OrganizationService)
  private _usage = new BehaviorSubject<SensorUsage>(null)
  private _sensors = new BehaviorSubject<Sensor[]>([])
  private _snackBar = inject(SnackBarService)

  dataLoggers$ = this._dataLoggers.asObservable()
  usage$ = this._usage.asObservable()
  sensors$ = this._sensors.asObservable()

  listDataLoggers(orgId: number, viewId: number) {
    const url = `/api/v3/data_loggers/?organization_id=${orgId}&property_view_id=${viewId}`
    this._httpClient
      .get<DataLogger[]>(url)
      .pipe(
        take(1),
        tap((dataLoggers) => {
          this._dataLoggers.next(dataLoggers)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching data loggers')
        }),
      )
      .subscribe()
  }

  listSensors(orgId: number, viewId: number) {
    const url = `/api/v3/properties/${viewId}/sensors/?organization_id=${orgId}`
    this._httpClient
      .get<Sensor[]>(url)
      .pipe(
        take(1),
        tap((sensors) => {
          this._sensors.next(sensors)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching sensors')
        }),
      )
      .subscribe()
  }

  listSensorUsage(orgId: number, viewId: number, config: SensorUsageRequestConfig = {}) {
    const { interval, showOnlyOccupiedReadings, page, per_page, excluded_sensor_ids } = {
      interval: 'Exact',
      showOnlyOccupiedReadings: false,
      page: 1,
      per_page: 1_000_000_000, // not an expensive request, just retrieve all (was 500)
      excluded_sensor_ids: [],
      ...config,
    }

    const params = new URLSearchParams({
      organization_id: orgId.toString(),
    })
    if (interval === 'Exact') {
      params.set('page', page.toString())
      params.set('per_page', per_page.toString())
    }

    const url = `/api/v3/properties/${viewId}/sensors/usage/?${params}`
    const body = { interval, showOnlyOccupiedReadings, excluded_sensor_ids }

    this._httpClient
      .post<SensorUsage>(url, body)
      .pipe(
        take(1),
        tap((usage) => {
          this._usage.next(usage)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching sensor usage')
        }),
      )
      .subscribe()
  }

  deleteSensor(orgId: number, viewId: number, sensorId: number) {
    const url = `/api/v3/properties/${viewId}/sensors/${sensorId}?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Sensor deleted successfully')
        this.listSensors(orgId, viewId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting sensor')
      }),
    )
  }

  deleteDataLogger(orgId: number, viewId: number, dataLoggerId: number) {
    const url = `/api/v3/data_loggers/${dataLoggerId}?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Sensor deleted successfully')
        this.listSensors(orgId, viewId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting sensor')
      }),
    )
  }

  updateSensor(orgId: number, viewId: number, sensorId: number, sensorData: Sensor) {
    const url = `/api/v3/properties/${viewId}/sensors/${sensorId}/?organization_id=${orgId}`
    return this._httpClient.put<Sensor>(url, sensorData).pipe(
      tap(() => {
        this._snackBar.success('Sensor updated successfully')
        this.listSensors(orgId, viewId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating sensor')
      }),
    )
  }

  updateDataLogger(orgId: number, viewId: number, dataLoggerId: number, dataLoggerData: DataLogger) {
    const url = `/api/v3/data_loggers/${dataLoggerId}/?organization_id=${orgId}`
    return this._httpClient.put<DataLogger>(url, dataLoggerData).pipe(
      tap(() => {
        this._snackBar.success('Data Logger updated successfully')
        this.listDataLoggers(orgId, viewId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating data logger')
      }),
    )
  }

  createDataLogger(orgId: number, viewId: number, dataLoggerData: DataLogger) {
    const url = `/api/v3/data_loggers/?organization_id=${orgId}&property_view_id=${viewId}`
    return this._httpClient.post<DataLogger>(url, dataLoggerData).pipe(
      tap(() => {
        this._snackBar.success('Data Logger created successfully')
        this.listDataLoggers(orgId, viewId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating data logger')
      }),
    )
  }
}
