import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { BehaviorSubject, catchError, map, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type { Program, ProgramData, ProgramResponse, ProgramsResponse, ProgramUpsertPayload } from './program.types'

@Injectable({ providedIn: 'root' })
export class ProgramService {
  private _httpClient = inject(HttpClient)
  private _programs = new BehaviorSubject<Program[]>([])
  // private _programs = new ReplaySubject<Program[]>(1)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)
  programs$ = this._programs
  orgId: number

  constructor() {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.list(orgId)
        }),
      )
      .subscribe()
  }

  list(orgId: number) {
    const url = `/api/v3/compliance_metrics/?organization_id=${orgId}`
    this._httpClient
      .get<ProgramsResponse>(url)
      .pipe(
        map(({ compliance_metrics }) => {
          this.programs$.next(compliance_metrics)
          return compliance_metrics
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching Programs')
        }),
      )
      .subscribe()
  }

  create(orgId: number, data: ProgramUpsertPayload): Observable<ProgramResponse> {
    const url = `/api/v3/compliance_metrics/?organization_id=${orgId}`
    const payload = this._normalizePayload(data)
    return this._httpClient.post<ProgramResponse>(url, payload).pipe(
      tap(() => {
        this.list(orgId)
        this._snackBar.success('Successfully created Program')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating Program')
      }),
    )
  }

  update(orgId: number, programId: number, data: ProgramUpsertPayload): Observable<ProgramResponse> {
    const url = `/api/v3/compliance_metrics/${programId}/?organization_id=${orgId}`
    const payload = this._normalizePayload(data)
    return this._httpClient.put<ProgramResponse>(url, payload).pipe(
      tap(() => {
        this.list(orgId)
        this._snackBar.success('Successfully updated Program')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating Program')
      }),
    )
  }

  delete(orgId: number, programId: number): Observable<ProgramResponse> {
    const url = `/api/v3/compliance_metrics/${programId}/?organization_id=${orgId}`
    return this._httpClient.delete<ProgramResponse>(url).pipe(
      tap(() => {
        this.list(orgId)
        this._snackBar.success('Successfully deleted Program')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting Program')
      }),
    )
  }

  evaluate(orgId: number, programId: number, aliId: number = null): Observable<ProgramData> {
    let url = `/api/v3/compliance_metrics/${programId}/evaluate/?organization_id=${orgId}`
    if (aliId) url += `&access_level_instance_id=${aliId}`

    return this._httpClient.get<{ data: ProgramData }>(url).pipe(
      map(({ data }) => data),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error evaluating Program')
      }),
    )
  }

  private _normalizePayload(data: ProgramUpsertPayload): ProgramUpsertPayload {
    const payload = { ...data } as ProgramUpsertPayload & Partial<Program>
    delete payload.organization_id
    delete payload.id
    delete payload.energy_bool
    delete payload.emission_bool

    return {
      ...payload,
      actual_emission_column: payload.actual_emission_column ?? null,
      actual_energy_column: payload.actual_energy_column ?? null,
      cycles: payload.cycles ?? [],
      emission_metric_type: payload.emission_metric_type ?? '',
      energy_metric_type: payload.energy_metric_type ?? '',
      filter_group: payload.filter_group ?? null,
      target_emission_column: payload.target_emission_column ?? null,
      target_energy_column: payload.target_energy_column ?? null,
      x_axis_columns: payload.x_axis_columns ?? [],
    }
  }
}
