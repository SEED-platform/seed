import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, map, ReplaySubject } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type {
  BbSalesforceConfig,
  BbSalesforceConfigResponse,
  BbSalesforceConfigsResponse,
  BbSalesforceLoginUrlResponse,
  BbSalesforceLogoutResponse,
  BbSalesforceTokenResponse,
  BbSalesforceVerifyTokenResponse,
} from './salesforce.types'

@Injectable({ providedIn: 'root' })
export class BbSalesforceService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)

  private _config = new ReplaySubject<BbSalesforceConfig>(1)

  config$ = this._config.asObservable()

  constructor() {
    this._userService.currentOrganizationId$.subscribe((organizationId) => {
      this.getConfig(organizationId).subscribe()
    })
  }

  getConfig(organizationId: number): Observable<BbSalesforceConfigsResponse> {
    const url = `/api/v3/bb_salesforce/configs/?organization_id=${organizationId}`
    return this._httpClient.get<BbSalesforceConfigsResponse>(url).pipe(
      map((response) => {
        // API returns a single config object or {} when none exists
        this._config.next(response.bb_salesforce_configs ?? ({} as BbSalesforceConfig))
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching BB Salesforce config')
      }),
    )
  }

  create(organizationId: number, config: Partial<BbSalesforceConfig>): Observable<BbSalesforceConfig> {
    const url = `/api/v3/bb_salesforce/configs/?organization_id=${organizationId}`
    return this._httpClient.post<BbSalesforceConfigResponse>(url, { ...config }).pipe(
      map((response) => {
        this._config.next(response.bb_salesforce_config)
        return response.bb_salesforce_config
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating BB Salesforce config')
      }),
    )
  }

  update(organizationId: number, config: Partial<BbSalesforceConfig>): Observable<BbSalesforceConfig> {
    const url = `/api/v3/bb_salesforce/configs/update_config/?organization_id=${organizationId}`
    return this._httpClient.put<BbSalesforceConfigResponse>(url, { ...config }).pipe(
      map((response) => {
        this._snackBar.success('BB Salesforce configuration updated')
        this._config.next(response.bb_salesforce_config)
        return response.bb_salesforce_config
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating BB Salesforce config')
      }),
    )
  }

  delete(organizationId: number, configId: number): Observable<object> {
    const url = `/api/v3/bb_salesforce/configs/${configId}/?organization_id=${organizationId}`
    return this._httpClient.delete(url).pipe(
      map(() => {
        this._config.next({} as BbSalesforceConfig)
        return {}
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting BB Salesforce config')
      }),
    )
  }

  getLoginUrl(organizationId: number): Observable<BbSalesforceLoginUrlResponse> {
    const url = `/api/v3/bb_salesforce/login_url/?organization_id=${organizationId}`
    return this._httpClient.get<BbSalesforceLoginUrlResponse>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Cannot login to Salesforce. Double check the Salesforce login URL.')
      }),
    )
  }

  getToken(code: string, organizationId: number): Observable<BbSalesforceTokenResponse> {
    const url = `/api/v3/bb_salesforce/get_token/?code=${code}&organization_id=${organizationId}`
    return this._httpClient.get<BbSalesforceTokenResponse>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error exchanging Salesforce authorization code')
      }),
    )
  }

  logout(organizationId: number): Observable<BbSalesforceLogoutResponse> {
    const url = `/api/v3/bb_salesforce/logout/?organization_id=${organizationId}`
    return this._httpClient.get<BbSalesforceLogoutResponse>(url).pipe(
      map((response) => {
        this._snackBar.success('Successfully logged out of Salesforce')
        return response
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error logging out of Salesforce')
      }),
    )
  }

  verifyToken(organizationId: number): Observable<BbSalesforceVerifyTokenResponse> {
    const url = `/api/v3/bb_salesforce/verify_token/?organization_id=${organizationId}`
    return this._httpClient.get<BbSalesforceVerifyTokenResponse>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error verifying Salesforce token')
      }),
    )
  }
}
