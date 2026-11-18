import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, Subject, takeUntil, tap } from 'rxjs'
import { ErrorService } from '@seed/services'
import { UserService } from '../user'
import type {
  getPartnersResponse,
  getTokenResponse,
  loginUrlResponse,
  SalesforcePortfolioConfig,
  SalesforcePortfolioConfigResponse,
  verifyTokenResponse,
} from './salesforce-portfolio.types'

@Injectable({
  providedIn: 'root',
})
export class SalesforcePortfolioService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  orgId: number

  constructor() {
    this._userService.currentOrganizationId$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((orgId) => {
          this.orgId = orgId
        }),
      )
      .subscribe()
  }

  getConfig(organizationId: number): Observable<SalesforcePortfolioConfig> {
    const url = `/api/v3/bb_salesforce/configs/?organization_id=${organizationId}`
    return this._httpClient.get<SalesforcePortfolioConfigResponse>(url).pipe(
      map((response) => response.bb_salesforce_configs),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  getToken(code: string, organizationId: number): Observable<getTokenResponse> {
    const url = `/api/v3/bb_salesforce/get_token/?organization_id=${organizationId}&code=${code}`
    return this._httpClient.get<getTokenResponse>(url).pipe(
      map((response) => response),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  getPartners(organizationId: number): Observable<getPartnersResponse> {
    const url = `/api/v3/bb_salesforce/partners/?organization_id=${organizationId}`
    return this._httpClient.get<getPartnersResponse>(url).pipe(
      map((response) => response),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  getAnnualReports(goalId: number): Observable<getPartnersResponse> {
    const url = `/api/v3/bb_salesforce/annual_report/?organization_id=${this.orgId}&goal_id=${goalId}`
    return this._httpClient.get<getPartnersResponse>(url).pipe(
      map((response) => response),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  updateConfig(updatedSalesforcePortfolioConfig: SalesforcePortfolioConfig, organizationId: number): Observable<SalesforcePortfolioConfig> {
    const url = `/api/v3/bb_salesforce/configs/update_config/?organization_id=${organizationId}`
    return this._httpClient.put<SalesforcePortfolioConfigResponse>(url, { ...updatedSalesforcePortfolioConfig }).pipe(
      map((response) => response.bb_salesforce_configs),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  verifyToken(organizationId: number): Observable<verifyTokenResponse> {
    const url = `/api/v3/bb_salesforce/verify_token/?organization_id=${organizationId}`
    return this._httpClient.get<verifyTokenResponse>(url).pipe(
      map((response) => response),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  getLoginUrl(organizationId: number): Observable<loginUrlResponse> {
    const url = `/api/v3/bb_salesforce/login_url/?organization_id=${organizationId}`
    return this._httpClient.get<loginUrlResponse>(url).pipe(
      map((response) => response),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }
}
