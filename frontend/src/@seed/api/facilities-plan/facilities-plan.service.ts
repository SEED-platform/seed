import type { HttpErrorResponse, HttpResponse } from '@angular/common/http'
import { HttpClient, HttpContext } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { BehaviorSubject, catchError, map, tap } from 'rxjs'
import { ErrorService, SKIP_LOADING } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type { FacilitiesPlan, FacilitiesPlanResponse, FacilitiesPlansResponse, FacilitiesPlanUpsertPayload } from './facilities-plan.types'

@Injectable({ providedIn: 'root' })
export class FacilitiesPlanService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)
  private _facilitiesPlans = new BehaviorSubject<FacilitiesPlan[]>([])

  facilitiesPlans$ = this._facilitiesPlans.asObservable()
  orgId: number

  constructor() {
    this._userService.currentOrganizationId$.subscribe((id) => {
      this.orgId = id
      this.list()
    })
  }

  list(): void {
    const url = `/api/v3/facilities_plans/?organization_id=${this.orgId}`
    this._httpClient
      .get<FacilitiesPlansResponse>(url, { context: new HttpContext().set(SKIP_LOADING, true) })
      .pipe(
        map(({ data }) => data),
        tap((plans) => {
          this._facilitiesPlans.next(plans)
        }),
        catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error fetching Facilities Plans')),
      )
      .subscribe()
  }

  create(data: FacilitiesPlanUpsertPayload): Observable<FacilitiesPlanResponse> {
    const url = `/api/v3/facilities_plans/?organization_id=${this.orgId}`
    return this._httpClient.post<FacilitiesPlanResponse>(url, { ...data, organization: this.orgId }).pipe(
      tap(() => {
        this.list()
        this._snackBar.success('Facilities Plan created')
      }),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error creating Facilities Plan')),
    )
  }

  update(planId: number, data: FacilitiesPlanUpsertPayload): Observable<FacilitiesPlanResponse> {
    const url = `/api/v3/facilities_plans/${planId}/?organization_id=${this.orgId}`
    return this._httpClient.put<FacilitiesPlanResponse>(url, { ...data, organization: this.orgId }).pipe(
      tap(() => {
        this.list()
        this._snackBar.success('Facilities Plan updated')
      }),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error updating Facilities Plan')),
    )
  }

  delete(planId: number): Observable<HttpResponse<null>> {
    const url = `/api/v3/facilities_plans/${planId}/?organization_id=${this.orgId}`
    return this._httpClient.delete<HttpResponse<null>>(url).pipe(
      tap(() => {
        this.list()
        this._snackBar.success('Facilities Plan deleted')
      }),
      catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error deleting Facilities Plan')),
    )
  }
}
