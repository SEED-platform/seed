import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject, Subject, takeUntil, tap } from 'rxjs'
import { ErrorService } from '@seed/services/error/error.service'
import type { MeterTypeWithUnitsResponse, MeterWithUnits } from './meter-types.types'

@Injectable({ providedIn: 'root' })
export class MeterTypesService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _energyMeters = new ReplaySubject<MeterWithUnits[]>(1)
  private _waterMeters = new ReplaySubject<MeterWithUnits[]>(1)
  energyMeters$ = this._energyMeters.asObservable()
  waterMeters$ = this._waterMeters.asObservable()

  constructor() {
    this.getMeters().pipe(takeUntil(this._unsubscribeAll$)).subscribe()
  }

  getMeters(): Observable<MeterTypeWithUnitsResponse> {
    const url = '/api/v3/properties/valid_meter_types_and_units/'
    return this._httpClient.get<MeterTypeWithUnitsResponse>(url).pipe(
      tap((response) => {
        this._energyMeters.next(
          Object.keys(response.energy).map((e) => {
            return { name: e, units: response.energy[e] }
          }),
        )
        this._waterMeters.next(
          Object.keys(response.water).map((w) => {
            return { name: w, units: response.water[w] }
          }),
        )
      }),
      map((response) => {
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        // TODO need to figure out error handling
        return this._errorService.handleError(error, 'Error fetching audit template configs')
      }),
    )
  }
}
