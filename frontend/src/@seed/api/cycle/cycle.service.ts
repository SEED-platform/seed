import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { BehaviorSubject, catchError, map, take, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type { Cycle, CycleResponse, CyclesResponse } from './cycle.types'

@Injectable({ providedIn: 'root' })
export class CycleService {
  private _httpClient = inject(HttpClient)
  private _userService = inject(UserService)
  private _snackBar = inject(SnackBarService)
  private _errorService = inject(ErrorService)
  private _cycles = new BehaviorSubject<Cycle[]>([])
  orgId: number

  cycles$ = this._cycles.asObservable()

  constructor() {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.getCycles(orgId)
        }),
      )
      .subscribe()
  }

  getCycles(orgId: number) {
    const url = `/api/v3/cycles/?organization_id=${orgId}`
    this._httpClient
      .get<CyclesResponse>(url)
      .pipe(
        map(({ cycles }) => cycles),
        tap((cycles) => {
          this._cycles.next(cycles)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching cycles')
        }),
      )
      .subscribe()
  }

  getCycle(orgId: number, cycleId: number): Observable<Cycle> {
    const url = `/api/v3/cycles/${cycleId}?organization_id=${orgId}`
    return this._httpClient.get<CycleResponse>(url).pipe(
      take(1),
      map(({ cycles }) => cycles),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching cycles')
      }),
    )
  }

  post({ data, orgId }): Observable<CycleResponse | null> {
    const url = `/api/v3/cycles/?organization_id=${orgId}`
    return this._httpClient.post<CycleResponse>(url, data).pipe(
      tap((response) => {
        this._snackBar.success(`Created Cycle ${response.cycles.name}`)
        this.getCycles(orgId as number)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating cycle')
      }),
    )
  }

  put({ data, id, orgId }): Observable<CycleResponse | null> {
    const url = `/api/v3/cycles/${id}/?organization_id=${orgId}`
    return this._httpClient.put<CycleResponse>(url, data).pipe(
      tap((response) => {
        this._snackBar.success(`Updated Cycle ${response.cycles.name}`)
        this.getCycles(orgId as number)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating cycle')
      }),
    )
  }

  delete(id: number, orgId: number) {
    const url = `/api/v3/cycles/${id}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this.getCycles(orgId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting cycle')
      }),
    )
  }
}
