import type { HttpErrorResponse, HttpResponse } from '@angular/common/http'
import { HttpClient, HttpContext, HttpParams } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { BehaviorSubject, catchError, map, tap } from 'rxjs'
import { ErrorService, SKIP_LOADING } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type {
  FacilitiesPlanRun,
  FacilitiesPlanRunColumnFilter,
  FacilitiesPlanRunColumnSort,
  FacilitiesPlanRunCreatePayload,
  FacilitiesPlanRunIdsResponse,
  FacilitiesPlanRunPropertiesResponse,
  FacilitiesPlanRunsResponse,
  FacilitiesPlanRunUpdatePayload,
} from './facilities-plan-run.types'

@Injectable({ providedIn: 'root' })
export class FacilitiesPlanRunService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)
  private _facilitiesPlanRuns = new BehaviorSubject<FacilitiesPlanRun[]>([])

  facilitiesPlanRuns$ = this._facilitiesPlanRuns.asObservable()
  orgId: number

  constructor() {
    this._userService.currentOrganizationId$.subscribe((id) => {
      this.orgId = id
      this.list()
    })
  }

  list(): void {
    const url = `/api/v3/facilities_plan_runs/?organization_id=${this.orgId}`
    this._httpClient
      .get<FacilitiesPlanRunsResponse>(url, { context: new HttpContext().set(SKIP_LOADING, true) })
      .pipe(
        map(({ data }) => data),
        tap((runs) => {
          this._facilitiesPlanRuns.next(runs)
        }),
        catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error fetching Facilities Plan Runs')),
      )
      .subscribe()
  }

  create(data: FacilitiesPlanRunCreatePayload): Observable<FacilitiesPlanRun> {
    const url = `/api/v3/facilities_plan_runs/?organization_id=${this.orgId}`
    return this._httpClient.post<FacilitiesPlanRun>(url, data).pipe(
      tap(() => {
        this.list()
        this._snackBar.success('Facilities Plan Run created')
      }),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error creating Facilities Plan Run')),
    )
  }

  update(runId: number, data: FacilitiesPlanRunUpdatePayload): Observable<FacilitiesPlanRun> {
    const url = `/api/v3/facilities_plan_runs/${runId}/?organization_id=${this.orgId}`
    return this._httpClient.put<FacilitiesPlanRun>(url, data).pipe(
      tap(() => {
        this.list()
        this._snackBar.success('Facilities Plan Run updated')
      }),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error updating Facilities Plan Run')),
    )
  }

  delete(runId: number): Observable<HttpResponse<null>> {
    const url = `/api/v3/facilities_plan_runs/${runId}/?organization_id=${this.orgId}`
    return this._httpClient.delete<HttpResponse<null>>(url).pipe(
      tap(() => {
        this.list()
        this._snackBar.success('Facilities Plan Run deleted')
      }),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error deleting Facilities Plan Run')),
    )
  }

  getProperties(
    runId: number,
    page: number,
    perPage: number,
    filters: FacilitiesPlanRunColumnFilter[],
    sorts: FacilitiesPlanRunColumnSort[],
  ): Observable<FacilitiesPlanRunPropertiesResponse> {
    let params = new HttpParams().set('organization_id', this.orgId).set('page', page).set('per_page', perPage)
    for (const [k, v] of Object.entries(this._formatFilters(filters))) {
      params = params.set(k, v)
    }
    for (const s of this._formatSortsList(sorts)) {
      params = params.append('order_by', s)
    }
    return this._httpClient
      .get<FacilitiesPlanRunPropertiesResponse>(`/api/v3/facilities_plan_runs/${runId}/properties/`, { params })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error fetching Facilities Plan properties')))
  }

  getAllIds(runId: number, filters: FacilitiesPlanRunColumnFilter[]): Observable<FacilitiesPlanRunIdsResponse> {
    let params = new HttpParams().set('organization_id', this.orgId).set('only_ids', true)
    for (const [k, v] of Object.entries(this._formatFilters(filters))) {
      params = params.set(k, v)
    }
    return this._httpClient
      .get<FacilitiesPlanRunIdsResponse>(`/api/v3/facilities_plan_runs/${runId}/properties/`, { params })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error fetching all IDs')))
  }

  run(runId: number): Observable<FacilitiesPlanRun> {
    const url = `/api/v3/facilities_plan_runs/${runId}/run/?organization_id=${this.orgId}`
    return this._httpClient.post<FacilitiesPlanRun>(url, {}).pipe(
      tap(() => {
        this.list()
        this._snackBar.success('Facilities Plan calculated')
      }),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error running Facilities Plan')),
    )
  }

  export(runId: number): Observable<Blob> {
    const url = `/api/v3/facilities_plan_runs/${runId}/export/?organization_id=${this.orgId}`
    return this._httpClient
      .post(url, {}, { responseType: 'blob' })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error exporting Facilities Plan')))
  }

  private _formatFilters(filters: FacilitiesPlanRunColumnFilter[]): Record<string, string | number> {
    if (!filters?.length) return {}
    const result: Record<string, string | number> = {}
    for (const { name, operator, value } of filters) {
      result[`${name}__${operator}`] = value
    }
    return result
  }

  private _formatSortsList(sorts: FacilitiesPlanRunColumnSort[]): string[] {
    if (!sorts?.length) return []
    return sorts.sort((a, b) => a.priority - b.priority).map(({ name, direction }) => `${direction === 'desc' ? '-' : ''}${name}`)
  }
}
